import threading
import time
from datetime import datetime, timezone
from random import random
from typing import cast, Dict, Optional, List
from urllib.parse import urlparse

from aioredis import Redis
from communex.client import CommuneClient  # type: ignore
from communex.misc import get_map_modules
from communex.module.client import ModuleClient  # type: ignore
from communex.module.module import Module  # type: ignore
from communex.types import Ss58Address  # type: ignore
from src.subnet.validator.helpers.ipfs_utils import fetch_file_from_ipfs
from loguru import logger
from substrateinterface import Keypair  # type: ignore
from ._config import ValidatorSettings

from src.subnet.validator.helpers.helpers import raise_exception_if_not_registered, get_ip_port, cut_to_max_allowed_weights
from .weights_storage import WeightsStorage
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.protocol import Discovery
from src.subnet.validator.database.models.tweet_cache import TweetCacheManager
from src.subnet.validator.database.models.user_cache import UserCacheManager
from .twitter import TwitterService
from .. import VERSION


class Validator(Module):

    def __init__(
            self,
            key: Keypair,
            netuid: int,
            client: CommuneClient,
            weights_storage: WeightsStorage,
            miner_discovery_manager: MinerDiscoveryManager,
            tweet_cache_manager: TweetCacheManager,
            user_cache_manager: UserCacheManager,
            twitter_service: TwitterService,
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
        self.tweet_cache_manager = tweet_cache_manager
        self.user_cache_manager = user_cache_manager
        self.twitter_service = twitter_service
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
            dataset = await self.fetch_dataset(dataset_link)
            if not dataset:
                logger.error("Failed to fetch dataset.")
                return None

            if not self.validate_json_dataset(dataset):
                logger.error("Dataset validation failed.")
                return None

            return dataset
        except Exception as e:
            logger.error(f"Error fetching or validating dataset: {e}")
            return None

    @staticmethod
    def validate_json_dataset(dataset: List[Dict]) -> bool:
        """
        Validates the structure, completeness, and integrity of the dataset.

        Args:
            dataset (List[Dict]): The dataset to validate.

        Returns:
            bool: True if the dataset is valid, False otherwise.
        """
        # Required fields for the dataset
        required_fields = {"token", "tweet", "user_account", "region", "edges"}
        required_tweet_fields = {"id", "url", "text", "likes", "images", "timestamp"}
        required_user_fields = {"username", "user_id", "is_verified", "follower_count", "account_age",
                                "engagement_level", "total_tweets"}
        required_region_fields = {"name"}
        required_edge_fields = {"type", "from", "to", "attributes"}

        if not isinstance(dataset, list):
            print("Dataset is not a list.")
            return False

        token_found = False

        for index, entry in enumerate(dataset):
            if not isinstance(entry, dict):
                print(f"Entry at index {index} is not a dictionary.")
                return False

            # Check for missing required fields
            missing_fields = required_fields - entry.keys()
            if missing_fields:
                print(f"Entry at index {index} is missing fields: {missing_fields}")
                return False

            # Validate 'token'
            if not isinstance(entry["token"], str) or not entry["token"].strip():
                print(f"Invalid 'token' in entry at index {index}.")
                return False
            token_found = True

            # Validate 'tweet' fields
            tweet = entry["tweet"]
            if not isinstance(tweet, dict):
                print(f"'tweet' is not a dictionary in entry at index {index}.")
                return False

            missing_tweet_fields = required_tweet_fields - tweet.keys()
            if missing_tweet_fields:
                print(f"Tweet in entry at index {index} is missing fields: {missing_tweet_fields}")
                return False

            try:
                datetime.fromisoformat(tweet["timestamp"])
            except (ValueError, TypeError):
                print(f"Invalid 'timestamp' in tweet at index {index}.")
                return False

            if not isinstance(tweet["likes"], int) or tweet["likes"] < 0:
                print(f"Invalid 'likes' in tweet at index {index}.")
                return False

            if not isinstance(tweet["images"], list):
                print(f"'images' is not a list in tweet at index {index}.")
                return False

            # Validate 'user_account' fields
            user_account = entry["user_account"]
            if not isinstance(user_account, dict):
                print(f"'user_account' is not a dictionary in entry at index {index}.")
                return False

            missing_user_fields = required_user_fields - user_account.keys()
            if missing_user_fields:
                print(f"User account in entry at index {index} is missing fields: {missing_user_fields}")
                return False

            try:
                datetime.fromisoformat(user_account["account_age"])
            except (ValueError, TypeError):
                print(f"Invalid 'account_age' in user account at index {index}.")
                return False

            if not isinstance(user_account["follower_count"], int) or user_account["follower_count"] < 0:
                print(f"Invalid 'follower_count' in user account at index {index}.")
                return False

            if not isinstance(user_account["engagement_level"], int) or user_account["engagement_level"] < 0:
                print(f"Invalid 'engagement_level' in user account at index {index}.")
                return False

            if not isinstance(user_account["total_tweets"], int) or user_account["total_tweets"] < 0:
                print(f"Invalid 'total_tweets' in user account at index {index}.")
                return False

            # Validate 'region' fields
            region = entry["region"]
            if not isinstance(region, dict):
                print(f"'region' is not a dictionary in entry at index {index}.")
                return False

            missing_region_fields = required_region_fields - region.keys()
            if missing_region_fields:
                print(f"Region in entry at index {index} is missing fields: {missing_region_fields}")
                return False

            # Validate 'edges'
            edges = entry["edges"]
            if not isinstance(edges, list):
                print(f"'edges' is not a list in entry at index {index}.")
                return False

            for edge in edges:
                if not isinstance(edge, dict):
                    print(f"An edge in entry at index {index} is not a dictionary.")
                    return False

                missing_edge_fields = required_edge_fields - edge.keys()
                if missing_edge_fields:
                    print(f"An edge in entry at index {index} is missing fields: {missing_edge_fields}")
                    return False

                if not isinstance(edge["attributes"], dict):
                    print(f"'attributes' in edge at index {index} is not a dictionary.")
                    return False

        if not token_found:
            print("No valid 'token' field found in the dataset.")
            return False

        print("Dataset is valid.")
        return True

    async def score_dataset(self, dataset: Dict, sample_size: int = 3) -> Dict[str, float]:
        """
        Scores a dataset based on tweet and user account validation.

        Args:
            dataset (Dict): The dataset to score.
            sample_size (int): Number of random entries to validate per category.

        Returns:
            Dict[str, float]: A dictionary with scoring details.
        """
        scores = {}

        if "entries" not in dataset or not isinstance(dataset["entries"], list):
            logger.error("Invalid dataset format: 'entries' missing or not a list.")
            return {"overall_score": 0.0}

        total_entries = len(dataset["entries"])
        if total_entries == 0:
            logger.error("Dataset contains no entries.")
            return {"overall_score": 0.0}

        tweet_scores = []
        user_scores = []

        sampled_entries = random.sample(dataset["entries"], min(sample_size, total_entries))
        for entry in sampled_entries:
            tweet_score = await self._validate_tweet(entry.get("tweet"))
            user_score = await self._validate_user(entry.get("user_account"))

            if tweet_score is not None:
                tweet_scores.append(tweet_score)
            if user_score is not None:
                user_scores.append(user_score)

        avg_tweet_score = sum(tweet_scores) / len(tweet_scores) if tweet_scores else 0.0
        avg_user_score = sum(user_scores) / len(user_scores) if user_scores else 0.0

        overall_score = (avg_tweet_score + avg_user_score) / 2
        scores.update({
            "tweet_score": avg_tweet_score,
            "user_score": avg_user_score,
            "overall_score": overall_score
        })

        logger.info(f"Dataset scored: {scores}")
        return scores

    async def _validate_tweet(self, tweet: Dict) -> Optional[float]:
        """
        Validates a tweet entry by checking its data against the cache or API.

        Args:
            tweet (Dict): The tweet data to validate.

        Returns:
            Optional[float]: A score for the tweet entry, or None if invalid.
        """
        if not tweet or not isinstance(tweet, dict):
            logger.warning("Invalid tweet format.")
            return None

        tweet_id = tweet.get("id")
        tweet_date = tweet.get("timestamp")

        try:
            if not tweet_id or not isinstance(tweet_id, str):
                logger.warning("Missing or invalid tweet ID.")
                return None

            cached_tweet = await self.tweet_cache_manager.get_tweet_cache(tweet_id)
            if cached_tweet:
                logger.info(f"Tweet data retrieved from cache for tweet_id {tweet_id}")
                cached_date = datetime.fromisoformat(cached_tweet["tweet_date"])
            else:
                fetched_tweet = self.twitter_service.get_tweet_details(tweet_id)
                if not fetched_tweet:
                    logger.warning(f"Tweet not found for tweet_id {tweet_id}.")
                    return 0.0

                cached_date = (
                    datetime.fromisoformat(fetched_tweet.created_at.replace("Z", "+00:00")).astimezone(
                        timezone.utc).replace(tzinfo=None)
                    if isinstance(fetched_tweet.created_at, str)
                    else fetched_tweet.created_at.astimezone(timezone.utc).replace(tzinfo=None)
                )
                await self.tweet_cache_manager.store_tweet_cache(tweet_id=tweet_id, tweet_date=cached_date.isoformat())

            actual_date = datetime.fromisoformat(tweet_date.replace("Z", "+00:00")).astimezone(timezone.utc).replace(
                tzinfo=None)
            if actual_date != cached_date:
                logger.warning(
                    f"Tweet date mismatch for tweet_id {tweet_id}: expected {cached_date}, got {actual_date}.")
                return 0.5

            return 1.0
        except Exception as e:
            logger.error(f"Error validating tweet: {e}")
            return None

    async def _validate_user(self, user_account: Dict) -> Optional[float]:
        """
        Validates a user account entry by checking its data against the cache or API.

        Args:
            user_account (Dict): The user account data to validate.

        Returns:
            Optional[float]: A score for the user account entry, or None if invalid.
        """
        if not user_account or not isinstance(user_account, dict):
            logger.warning("Invalid user account format.")
            return None

        user_id = user_account.get("user_id")

        try:
            if not user_id or not isinstance(user_id, str):
                logger.warning("Missing or invalid user ID.")
                return None

            cached_user = await self.user_cache_manager.get_user_cache(user_id)
            if cached_user:
                logger.info(f"User data retrieved from cache for user_id {user_id}")
            else:
                fetched_user = self.twitter_service.get_user_details(user_id)
                if not fetched_user:
                    logger.warning(f"User not found for user_id {user_id}.")
                    return 0.0

                await self.user_cache_manager.store_user_cache(
                    user_id=user_id,
                    follower_count=fetched_user.followers_count,
                    verified=fetched_user.verified
                )

            return 1.0
        except Exception as e:
            logger.error(f"Error validating user: {e}")
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

    @staticmethod
    async def fetch_dataset(ipfs_identifier: str) -> dict:
        """
        Retrieve a dataset file from IPFS and return its content.

        Args:
            ipfs_identifier (str): The IPFS hash or full URL.

        Returns:
            dict: Dataset content as a dictionary.
        """
        try:
            # Extract hash if a full URL is passed
            if ipfs_identifier.startswith("http"):
                parsed_url = urlparse(ipfs_identifier)
                ipfs_hash = parsed_url.path.split('/')[-1]  # Extract the last part of the path
            else:
                ipfs_hash = ipfs_identifier

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
            module_ip, module_port = connection
            miner_key = miner_metadata['key']
            client = ModuleClient(module_ip, int(module_port), self.key)
            # Perform discovery and dataset validation
            discovery = await self._get_discovery(client, miner_key)
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
            # Update rank based on overall emissions or another external factor
            await self.miner_discovery_manager.update_miner_rank(miner_key, miner_metadata['emission'])

            dataset = await self._fetch_and_validate_dataset(discovery.dataset_link)
            if not dataset:
                logger.warning(f"Invalid dataset for miner {miner_key}. Excluding from scoring.")
                continue

            # Score dataset
            scores = await self.score_dataset(dataset)
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
