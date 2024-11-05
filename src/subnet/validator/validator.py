import asyncio
import json
import random
import threading
import time
import traceback
import uuid
from datetime import datetime
from random import sample
from typing import cast, Dict, Optional

from communex.client import CommuneClient  # type: ignore
from communex.errors import NetworkTimeoutError
from communex.misc import get_map_modules
from communex.module.client import ModuleClient  # type: ignore
from communex.module.module import Module  # type: ignore
from communex.types import Ss58Address  # type: ignore
from loguru import logger
from substrateinterface import Keypair  # type: ignore
from ._config import ValidatorSettings, load_base_weights

from .encryption import generate_hash
from .helpers import raise_exception_if_not_registered, get_ip_port, cut_to_max_allowed_weights
from .weights_storage import WeightsStorage
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.validator.database.models.miner_receipt import MinerReceiptManager
from src.subnet.protocol import TwitterChallenge, TwitterChallengesResponse, TwitterChallengeMinerResponse, Discovery
from .. import VERSION
from .twitter import TwitterService, TwitterUser


class Validator(Module):

    def __init__(
            self,
            key: Keypair,
            netuid: int,
            client: CommuneClient,
            weights_storage: WeightsStorage,
            miner_discovery_manager: MinerDiscoveryManager,
            miner_receipt_manager: MinerReceiptManager,
            twitter_service: TwitterService,
            query_timeout: int = 60,
            challenge_timeout: int = 60,

    ) -> None:
        super().__init__()

        self.miner_receipt_manager = miner_receipt_manager
        self.client = client
        self.key = key
        self.netuid = netuid
        self.challenge_timeout = challenge_timeout
        self.query_timeout = query_timeout
        self.weights_storage = weights_storage
        self.miner_discovery_manager = miner_discovery_manager
        self.twitter_service = twitter_service
        self.terminate_event = threading.Event()

    @staticmethod
    def get_addresses(client: CommuneClient, netuid: int) -> dict[int, str]:
        modules_adresses = client.query_map_address(netuid)
        for id, addr in modules_adresses.items():
            if addr.startswith('None'):
                port = addr.split(':')[1]
                modules_adresses[id] = f'0.0.0.0:{port}'
        logger.debug(f"Got modules addresses", modules_adresses=modules_adresses)
        return modules_adresses

    async def _challenge_miner(self, miner_info):
        start_time = time.time()
        try:
            connection, miner_metadata = miner_info
            module_ip, module_port = connection
            miner_key = miner_metadata['key']
            client = ModuleClient(module_ip, int(module_port), self.key)

            logger.info(f"Challenging miner", miner_key=miner_key)

            # Discovery Phase
            discovery = await self._get_discovery(client, miner_key)
            if not discovery:
                return None

            logger.debug(f"Got discovery for miner", miner_key=miner_key)

            # Challenge Phase
            challenge_response = await self._perform_challenges(client, miner_key, discovery)
            if not challenge_response:
                return None

            return TwitterChallengeMinerResponse(
                version=discovery.version,
                graph_db=discovery.graph_db,
                token=discovery.token,
                challenge_response=challenge_response,
            )
        except Exception as e:
            logger.error(f"Failed to challenge miner", error=e, miner_key=miner_key)
            return None
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"Execution time for challenge_miner", execution_time=execution_time, miner_key=miner_key)

    async def _get_discovery(self, client, miner_key) -> Discovery:
        try:
            discovery = await client.call(
                "discovery",
                miner_key,
                {"validator_version": str(VERSION), "validator_key": self.key.ss58_address},
                timeout=self.challenge_timeout,
            )

            return Discovery(**discovery)
        except Exception as e:
            logger.info(f"Miner failed to get discovery", miner_key=miner_key, error=e)
            return None

    async def _perform_challenges(self, client, miner_key, discovery) -> Optional[TwitterChallengeMinerResponse]:
        """
        Executes a Twitter challenge using TwitterService to check existence of tweet and user IDs,
        and validates verified status, follower count, and tweet creation date.
        """
        try:
            # Call the miner's challenge endpoint to retrieve Twitter data
            challenge_data = await client.call(
                "challenge",
                miner_key,
                {"validator_key": self.key.ss58_address},
                timeout=self.challenge_timeout,
            )

            token = challenge_data.get("token", discovery.token)
            output = challenge_data.get("output", {})

            tweet_id = output.get("tweet_id")
            user_id = output.get("user_id")
            expected_verified = output.get("verified")
            expected_follower_count = output.get("follower_count")
            expected_tweet_date = output.get("tweet_date")

            failed_challenges = 0
            actual_data = {}

            # 1. Check tweet existence and retrieve details
            tweet_data = self.twitter_service.get_tweet_details(tweet_id) if tweet_id else None
            if tweet_data:
                actual_data["tweet_date"] = tweet_data.created_at
                actual_data["tweet_id"] = tweet_id
            else:
                failed_challenges += 1
                logger.warning(f"Tweet not found on Twitter for tweet_id {tweet_id}")

            # 2. Check user existence and retrieve details
            user_data = self.twitter_service.get_user_details(user_id) if user_id else None
            if user_data:
                actual_data["verified"] = user_data.verified
                actual_data["follower_count"] = user_data.followers_count
                actual_data["user_id"] = user_id
            else:
                failed_challenges += 1
                logger.warning(f"User not found on Twitter for user_id {user_id}")

            # 3. Validate additional fields if IDs exist
            if tweet_data and tweet_data.created_at != expected_tweet_date:
                failed_challenges += 1
                logger.warning(f"Tweet date mismatch: expected {expected_tweet_date}, got {tweet_data.created_at}")
            if user_data:
                if user_data.verified != expected_verified:
                    failed_challenges += 1
                    logger.warning(f"Verified status mismatch: expected {expected_verified}, got {user_data.verified}")
                if user_data.followers_count != expected_follower_count:
                    failed_challenges += 1
                    logger.warning(
                        f"Follower count mismatch: expected {expected_follower_count}, got {user_data.followers_count}")

            # Construct TwitterChallengesResponse
            challenge_response = TwitterChallengesResponse(
                token=token,
                output=actual_data
            )

            # Return with failed challenge count
            return TwitterChallengeMinerResponse(
                token=token,
                version=discovery.version,
                graph_db=discovery.graph_db,
                challenge_response=challenge_response,
                failed_challenges=failed_challenges
            )

        except Exception as e:
            logger.error(f"Failed to perform Twitter challenge", error=e, miner_key=miner_key)
            return None

    @staticmethod
    def _score_miner(response: TwitterChallengeMinerResponse, receipt_miner_multiplier: float) -> float:
        if not response:
            logger.debug("Skipping empty response")
            return 0

        failed_challenges = response.failed_challenges

        # Set scoring based on failed challenges (up to 5)
        if failed_challenges == 5:
            return 0  # Full failure, no score
        elif failed_challenges == 4:
            return 0.1  # Minimal score for significant failure
        elif failed_challenges == 3:
            return 0.2
        elif failed_challenges == 2:
            return 0.4
        elif failed_challenges == 1:
            return 0.7  # Close to a perfect score but with a minor failure
        else:
            base_score = 1.0  # Perfect score if all checks are passed

        # Apply the receipt miner multiplier for the final score adjustment
        score = base_score * min(1.0, receipt_miner_multiplier)

        return score

    @staticmethod
    def adjust_network_weights_with_min_threshold(organic_prompts, min_threshold_ratio=5):
        base_weights = load_base_weights()
        total_base_weight = sum(base_weights.values())
        normalized_base_weights = {k: (v / total_base_weight) * 100 for k, v in base_weights.items()}
        num_networks = len(base_weights)
        min_threshold = 100 / min_threshold_ratio  # Minimum threshold percentage
        total_prompts = sum(organic_prompts.values())

        adjusted_weights = {}

        if total_prompts == 0:
            adjusted_weights = normalized_base_weights.copy()
        else:
            for network in normalized_base_weights.keys():
                organic_ratio = organic_prompts.get(network, 0) / total_prompts
                adjusted_weight = normalized_base_weights[network] * organic_ratio

                if adjusted_weight < min_threshold:
                    adjusted_weights[network] = min_threshold
                else:
                    adjusted_weights[network] = adjusted_weight

            total_adjusted_weight = sum(adjusted_weights.values())

            if total_adjusted_weight > 100:
                weight_above_min = total_adjusted_weight - (min_threshold * num_networks)
                if weight_above_min > 0:
                    scale_factor = (100 - (min_threshold * num_networks)) / weight_above_min
                    for network in adjusted_weights.keys():
                        if adjusted_weights[network] > min_threshold:
                            adjusted_weights[network] = min_threshold + (
                                        adjusted_weights[network] - min_threshold) * scale_factor
                else:
                    for network in adjusted_weights.keys():
                        adjusted_weights[network] = min_threshold

        return adjusted_weights

    async def validate_step(self, netuid: int, settings: ValidatorSettings) -> None:

        score_dict: dict[int, float] = {}
        miners_module_info = {}

        modules = cast(dict[str, Dict], get_map_modules(self.client, netuid=netuid, include_balances=False))
        modules_addresses = self.get_addresses(self.client, netuid)
        ip_ports = get_ip_port(modules_addresses)

        raise_exception_if_not_registered(self.key, modules)

        for key in modules.keys():
            module_meta_data = modules[key]
            uid = module_meta_data['uid']
            if uid not in ip_ports:
                continue
            module_addr = ip_ports[uid]
            miners_module_info[uid] = (module_addr, modules[key])

        logger.info(f"Found miners", miners_module_info=miners_module_info.keys())

        for _, miner_metadata in miners_module_info.values():
            await self.miner_discovery_manager.update_miner_rank(miner_metadata['key'], miner_metadata['emission'])

        challenge_tasks = []
        for uid, miner_info in miners_module_info.items():
            challenge_tasks.append(self._challenge_miner(miner_info))

        responses: tuple[TwitterChallengeMinerResponse] = await asyncio.gather(*challenge_tasks)

        for uid, miner_info, response in zip(miners_module_info.keys(), miners_module_info.values(), responses):
            if not response:
                score_dict[uid] = 0
                continue

            if isinstance(response, TwitterChallengeMinerResponse):
                network = response.network
                version = response.version
                graph_db = response.graph_db
                connection, miner_metadata = miner_info
                miner_address, miner_ip_port = connection
                miner_key = miner_metadata['key']

                organic_usage = await self.miner_receipt_manager.get_receipts_count_by_networks()
                adjusted_weights = self.adjust_network_weights_with_min_threshold(organic_usage, min_threshold_ratio=5)
                logger.debug(f"Adjusted weights", adjusted_weights=adjusted_weights, miner_key=miner_key)

                receipt_miner_multiplier_result = await self.miner_receipt_manager.get_receipt_miner_multiplier(network, miner_key)
                if not receipt_miner_multiplier_result:
                    receipt_miner_multiplier = 1
                else:
                    receipt_miner_multiplier = receipt_miner_multiplier_result[0]['multiplier']

                score = self._score_miner(response, receipt_miner_multiplier)

                weighted_score = 0
                total_weight = sum(adjusted_weights.values())
                weight = adjusted_weights[response.network]
                network_influence = weight / total_weight
                weighted_score += score * network_influence

                assert weighted_score <= 1
                score_dict[uid] = weighted_score

                await self.miner_discovery_manager.store_miner_metadata(uid, miner_key, miner_address, miner_ip_port, network, version, graph_db)
                await self.miner_discovery_manager.update_miner_challenges(miner_key, response.get_failed_challenges(), 2)

        if not score_dict:
            logger.info("No miner managed to give a valid answer")
            return None

        try:
            self.set_weights(settings, score_dict, self.netuid, self.client, self.key)
        except Exception as e:
            logger.error(f"Failed to set weights", error=e)

    def set_weights(self,
                    settings: ValidatorSettings,
                    score_dict: dict[
                        int, float
                    ],
                    netuid: int,
                    client: CommuneClient,
                    key: Keypair,
                    ) -> None:

        score_dict = cut_to_max_allowed_weights(score_dict, settings.MAX_ALLOWED_WEIGHTS)
        self.weights_storage.setup()
        weighted_scores: dict[int, int] = self.weights_storage.read()

        logger.debug(f"Setting weights for scores", score_dict=score_dict)
        score_sum = sum(score_dict.values())

        for uid, score in score_dict.items():
            if score_sum == 0:
                weight = 0
                weighted_scores[uid] = weight
            else:
                weight = int(score * 1000 / score_sum)
                weighted_scores[uid] = weight

        weighted_scores = {k: v for k, v in weighted_scores.items() if k in score_dict}

        self.weights_storage.store(weighted_scores)

        uids = list(weighted_scores.keys())
        weights = list(weighted_scores.values())

        if len(weighted_scores) > 0:
            client.vote(key=key, uids=uids, weights=weights, netuid=netuid)

        logger.info("Set weights", action="set_weight", timestamp=datetime.utcnow().isoformat(), weighted_scores=weighted_scores)

    async def validation_loop(self, settings: ValidatorSettings) -> None:
        while not self.terminate_event.is_set():
            start_time = time.time()
            await self.validate_step(self.netuid, settings)
            if self.terminate_event.is_set():
                logger.info("Terminating validation loop")
                break

            elapsed = time.time() - start_time
            if elapsed < settings.ITERATION_INTERVAL:
                sleep_time = settings.ITERATION_INTERVAL - elapsed
                logger.info(f"Sleeping for {sleep_time}")
                self.terminate_event.wait(sleep_time)
                if self.terminate_event.is_set():
                    logger.info("Terminating validation loop")
                    break

    async def query_miner(self, network: str, model_kind: str, query, miner_key: Optional[str]) -> dict:
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        query_hash = generate_hash(query)

        if miner_key:
            miner = await self.miner_discovery_manager.get_miner_by_key(miner_key, network)
            if not miner:
                return {
                    "request_id": request_id,
                    "timestamp": timestamp,
                    "miner_keys": None,
                    "query_hash": query_hash,
                    "model_kind": model_kind,
                    "query": query,
                    "response": []}

            response = await self._query_miner(miner, model_kind, query)
            await self.miner_receipt_manager.store_miner_receipt(request_id, miner_key, model_kind, network, query_hash, timestamp)

            return {
                "request_id": request_id,
                "timestamp": timestamp,
                "miner_keys": [miner_key],
                "query_hash": query_hash,
                "model_kind": model_kind,
                "query": query,
                "response": response
            }
        else:
            select_count = 3
            sample_size = 16
            miners = await self.miner_discovery_manager.get_miners_by_network(network)

            if len(miners) < 3:
                top_miners = miners
            else:
                top_miners = sample(miners[:sample_size], select_count)

            query_tasks = []
            for miner in top_miners:
                query_tasks.append(self._query_miner(miner,  model_kind, query))

            responses = await asyncio.gather(*query_tasks)

            combined_responses = list(zip(top_miners, responses))

            for miner, response in combined_responses:
                if response:
                    await self.miner_receipt_manager.store_miner_receipt(request_id, miner['miner_key'], model_kind, network, query_hash, timestamp)

            miner, random_response = random.choice(combined_responses)
            await self.miner_receipt_manager.accept_miner_receipt(request_id, miner['miner_key'])

            return {
                "request_id": request_id,
                "timestamp": timestamp,
                "miner_keys": [miner['miner_key'] for miner in top_miners],
                "query_hash": query_hash,
                "model_kind": model_kind,
                "query": query,
                "response": random_response
            }

    async def _query_miner(self, miner, model_kind, query):
        miner_key = miner['miner_key']
        miner_tokens = miner['tokens']
        module_ip = miner['miner_address']
        module_port = int(miner['miner_ip_port'])
        module_client = ModuleClient(module_ip, module_port, self.key)
        try:
            llm_query_result = await module_client.call(
                "query",
                miner_key,
                {"query": query, "validator_key": self.key.ss58_address},
                timeout=self.query_timeout,
            )
            if not llm_query_result:
                return None

            return llm_query_result
        except Exception as e:
            logger.warning(f"Failed to query miner", error=e, miner_key=miner_key)
            return None
