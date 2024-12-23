import threading
import time
from datetime import datetime
from typing import cast, Dict, Optional

from aioredis import Redis
from communex.client import CommuneClient  # type: ignore
from communex.misc import get_map_modules
from communex.module.client import ModuleClient  # type: ignore
from communex.module.module import Module  # type: ignore
from communex.types import Ss58Address  # type: ignore
from helpers.ipfs_utils import fetch_file_from_ipfs
from loguru import logger
from substrateinterface import Keypair  # type: ignore
from ._config import ValidatorSettings

from src.subnet.validator.helpers.helpers import raise_exception_if_not_registered, get_ip_port, cut_to_max_allowed_weights, validate_json_dataset, score_dataset
from .weights_storage import WeightsStorage
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.protocol import Discovery
from .. import VERSION


class Validator(Module):

    def __init__(
            self,
            key: Keypair,
            netuid: int,
            client: CommuneClient,
            weights_storage: WeightsStorage,
            miner_discovery_manager: MinerDiscoveryManager,
            redis_client: Redis,
            settings: ValidatorSettings
    ) -> None:
        super().__init__()

        self.client = client
        self.key = key
        self.netuid = netuid
        self.query_timeout = settings.QUERY_TIMEOUT
        self.snapshot_timeout = settings.SNAPSHOT_TIMEOUT
        self.weights_storage = weights_storage
        self.miner_discovery_manager = miner_discovery_manager
        self.terminate_event = threading.Event()
        self.redis_client = redis_client
        self.enable_gateway = settings.ENABLE_GATEWAY

    @staticmethod
    def get_addresses(client: CommuneClient, netuid: int) -> dict[int, str]:
        modules_adresses = client.query_map_address(netuid)
        for id, addr in modules_adresses.items():
            if addr.startswith('None'):
                port = addr.split(':')[1]
                modules_adresses[id] = f'0.0.0.0:{port}'
        logger.debug(f"Got modules addresses", modules_adresses=modules_adresses)
        return modules_adresses

    async def _get_discovery(self, client, miner_key) -> Optional[Discovery]:
        try:
            discovery = await client.call(
                "discovery",
                miner_key,
                {"validator_version": str(VERSION), "validator_key": self.key.ss58_address},
                timeout=self.query_timeout,
            )
            return Discovery(**discovery)
        except Exception as e:
            logger.info(f"Miner failed to get discovery", miner_key=miner_key, error=e)
            return None

    async def _fetch_and_validate_dataset(self, dataset_link: str) -> Optional[Dict]:
        """
        Fetches the dataset from the provided IPFS link and validates its structure and integrity.

        Args:
            dataset_link (str): The IPFS link to the dataset.

        Returns:
            Optional[Dict]: The validated dataset or None if invalid.
        """
        try:
            logger.info(f"Fetching dataset from IPFS: {dataset_link}")
            # Replace this with actual fetching logic
            dataset = await self.fetch_dataset(dataset_link)
            if not dataset:
                logger.error("Failed to fetch dataset.")
                return None

            if not validate_json_dataset(dataset):
                logger.error("Dataset validation failed.")
                return None

            return dataset
        except Exception as e:
            logger.error(f"Error fetching or validating dataset: {e}")
            return None

    @staticmethod
    def parse_dataset(file_content: str) -> dict:
        """
        Parse the dataset content into a dictionary.

        Args:
            file_content (str): Content of the dataset file.

        Returns:
            dict: Parsed dataset.
        """
        import json
        try:
            return json.loads(file_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse dataset content: {str(e)}")

    def fetch_dataset(ipfs_hash: str) -> dict:
        """
        Retrieve a dataset file from IPFS and return its content.

        Args:
            ipfs_hash (str): The IPFS hash of the dataset file.

        Returns:
            dict: Dataset content as a dictionary.
        """
        try:
            file_content = fetch_file_from_ipfs(ipfs_hash)
            dataset = Validator.parse_dataset(file_content)
            return dataset
        except Exception as e:
            raise RuntimeError(f"Failed to fetch and parse dataset: {str(e)}")

    async def validate_step(self, netuid: int, settings: ValidatorSettings) -> None:
        score_dict: dict[int, float] = {}
        miners_module_info = {}

        # Get modules and their addresses
        modules = cast(dict[str, Dict], get_map_modules(self.client, netuid=netuid, include_balances=False))
        modules_addresses = self.get_addresses(self.client, netuid)
        ip_ports = get_ip_port(modules_addresses)

        raise_exception_if_not_registered(self.key, modules)

        # Populate miners_module_info with valid miners
        for key, module_meta_data in modules.items():
            uid = module_meta_data['uid']
            if uid not in ip_ports:
                continue
            module_addr = ip_ports[uid]
            miners_module_info[uid] = (module_addr, module_meta_data)

        logger.info(f"Found miners", miners_module_info=miners_module_info.keys())

        # Process miners
        valid_uids = set()
        for uid, miner_info in miners_module_info.items():
            connection, miner_metadata = miner_info
            miner_key = miner_metadata['key']

            # Perform discovery and dataset validation
            discovery = await self._get_discovery(self.client, miner_key)
            if not discovery or not discovery.dataset_link:
                logger.warning(f"No dataset link found for miner {miner_key}. Excluding from scoring.")
                continue

            # Store discovered miner metadata
            await self.miner_discovery_manager.store_miner_metadata(
                uid=uid,
                miner_key=miner_key,
                miner_address=connection[0],
                miner_ip_port=connection[1],
                token=discovery.token,
                version=discovery.version,
                ipfs_link=discovery.dataset_link
            )

            dataset = await self._fetch_and_validate_dataset(discovery.dataset_link)
            if not dataset:
                logger.warning(f"Invalid dataset for miner {miner_key}. Excluding from scoring.")
                continue

            # Score dataset
            scores = score_dataset(dataset)
            total_score = sum(scores.values()) / len(scores)
            score_dict[uid] = total_score
            valid_uids.add(uid)

        # Log excluded miners
        excluded_uids = set(miners_module_info.keys()) - valid_uids
        if excluded_uids:
            logger.info(f"Excluded miners: {excluded_uids}")

        # Set weights based on scores
        if score_dict:
            try:
                self.set_weights(settings, score_dict, self.netuid, self.client, self.key)
            except Exception as e:
                logger.error(f"Failed to set weights", error=e)
        else:
            logger.info("No valid miners found in this validation step.")

    def set_weights(self, settings: ValidatorSettings, score_dict: dict[int, float], netuid: int, client: CommuneClient, key: Keypair) -> None:
        """
        Calculate and set weights for miners based on their scores.
        """
        score_dict = cut_to_max_allowed_weights(score_dict, settings.MAX_ALLOWED_WEIGHTS)
        self.weights_storage.setup()
        weighted_scores: dict[int, int] = self.weights_storage.read()

        logger.debug(f"Setting weights for scores", score_dict=score_dict)
        score_sum = sum(score_dict.values())

        for uid, score in score_dict.items():
            weight = int(score * 1000 / score_sum) if score_sum > 0 else 0
            weighted_scores[uid] = weight

        self.weights_storage.store(weighted_scores)

        uids = list(weighted_scores.keys())
        weights = list(weighted_scores.values())

        if uids:
            client.vote(key=key, uids=uids, weights=weights, netuid=netuid)

        logger.info("Set weights", action="set_weight", timestamp=datetime.utcnow().isoformat(), weighted_scores=weighted_scores)

    async def validation_loop(self, settings: ValidatorSettings) -> None:
        """
        Continuous validation loop with intervals.
        """
        while not self.terminate_event.is_set():
            start_time = time.time()
            await self.validate_step(self.netuid, settings)

            elapsed = time.time() - start_time
            if elapsed < settings.ITERATION_INTERVAL:
                sleep_time = settings.ITERATION_INTERVAL - elapsed
                logger.info(f"Sleeping for {sleep_time}")
                self.terminate_event.wait(sleep_time)
