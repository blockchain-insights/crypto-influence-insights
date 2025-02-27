import json
import os
import uuid

from jsonschema import validate, ValidationError
import math
import threading
import time
from datetime import datetime, timezone
from dateutil import parser
from random import sample
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
from .helpers.graph_search import GraphSearch
from .helpers.validator_graph_handler import ValidatorGraphHandler
from .weights_storage import WeightsStorage
from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.protocol import Discovery
from src.subnet.validator.database.models.tweet_cache import TweetCacheManager
from src.subnet.validator.database.models.user_cache import UserCacheManager
from src.subnet.validator.helpers.validator_graph_handler import ValidatorGraphHandler
from .twitter import TwitterService
from .. import VERSION
from .encryption import generate_hash

class Validator:
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
            graph_handler: ValidatorGraphHandler,
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
        self.graph_handler = graph_handler
        self.redis_client = redis_client
        self.settings = settings

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

    @staticmethod
    async def _fetch_and_validate_dataset(dataset_link: str, graph_handler: ValidatorGraphHandler,
                                          scrape_token: str, enable_gateway: bool) -> Optional[List[Dict]]:
        """
        Fetches the dataset from IPFS and validates it. Merges valid data into the graph.

        Args:
            dataset_link (str): The IPFS link to the dataset.
            graph_handler (ValidatorGraphHandler): Instance for handling graph operations.
            scrape_token (str): The scrape session token.

        Returns:
            Optional[List[Dict]]: The validated dataset or None if invalid.
        """
        try:
            # Dynamically determine the path to the schema file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            schema_path = os.path.join(base_dir, "..", "protocol", "dataset_schema.json")

            dataset = await Validator.fetch_dataset(dataset_link)
            if not dataset:
                logger.error("Failed to fetch dataset.")
                return None

            if not Validator.validate_json_dataset(dataset, schema_path):
                logger.error("Dataset validation failed.")
                return None

            # Merge valid data into Memgraph
            if not enable_gateway:
                logger.info("Gateway is disabled. Memgraph query functionality is not available.")
                logger.info("Dataset successfully fetched and validated.")
            else:
                graph_handler.merge_data(dataset, scrape_token)
                logger.info("Dataset successfully fetched, validated, and merged into the graph.")


            return dataset
        except Exception as e:
            logger.error(f"Error fetching or validating dataset: {e}")
            return None

    @staticmethod
    def load_schema(file_path: str) -> dict:
        """
        Load the JSON schema from a file.

        Args:
            file_path (str): Path to the schema file.

        Returns:
            dict: The loaded schema.
        """
        with open(file_path, "r") as file:
            return json.load(file)

    @staticmethod
    def validate_json_dataset(dataset: List[Dict], schema_path: str) -> bool:
        """
        Validates the dataset using the JSON schema.

        Args:
            dataset (List[Dict]): The dataset to validate.
            schema_path (str): Path to the JSON schema file.

        Returns:
            bool: True if the dataset is valid, False otherwise.
        """
        try:
            schema = Validator.load_schema(schema_path)
            validate(instance=dataset, schema=schema)
            logger.info("Dataset is valid.")
            return True
        except ValidationError as e:
            logger.error(f"Dataset validation error: {e.message}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e}")
            return False

    @staticmethod
    async def fetch_dataset(ipfs_identifier: str) -> List[Dict]:
        """
        Retrieve a dataset file from IPFS and return its content.

        Args:
            ipfs_identifier (str): The IPFS hash or full URL.

        Returns:
            List[Dict]: Dataset content as a list of dictionaries.
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

    @staticmethod
    def parse_dataset(file_content: str) -> List[Dict]:
        """
        Parse the dataset content into a list of dictionaries.

        Args:
            file_content (str): Content of the dataset file.

        Returns:
            List[Dict]: Parsed dataset.
        """
        try:
            return json.loads(file_content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse dataset content: {str(e)}")

    async def score_dataset(self, dataset: List[Dict], miner_key: str, sample_size: int = 3) -> Dict[str, float]:
        """
        Scores a dataset based on validation and data freshness. Blacklists miner if invalid IDs are detected.

        Args:
            dataset (List[Dict]): The dataset to score.
            miner_key (str): The unique identifier of the miner.
            sample_size (int): Number of random entries to validate per category.

        Returns:
            Dict[str, float]: A dictionary containing scoring details.
        """
        scores = {}

        # Check if the miner is blacklisted
        if await self.miner_discovery_manager.is_miner_blacklisted(miner_key):
            logger.warning(f"Miner {miner_key} is blacklisted. Skipping scoring.")
            return {"overall_score": 0.0}

        if not isinstance(dataset, list):
            logger.error("Invalid dataset format: dataset must be a list.")
            return {"overall_score": 0.0}

        total_entries = len(dataset)
        if total_entries == 0:
            logger.error("Dataset contains no entries.")
            return {"overall_score": 0.0}

        # Prioritize newer records in sampling by sorting
        sorted_dataset = sorted(dataset, key=lambda x: datetime.fromisoformat(x['tweet']['timestamp']), reverse=True)
        sampled_entries = sorted_dataset[:min(sample_size, total_entries)]

        # Validation results
        valid_tweets = 0
        valid_users = 0
        total_tweets = 0
        total_users = 0

        tweet_scores = []
        user_scores = []

        for entry in sampled_entries:
            tweet = entry.get("tweet")
            user_account = entry.get("user_account")

            # Validate tweet
            tweet_score = await self._validate_tweet(tweet)
            if tweet_score is not None:
                tweet_scores.append(tweet_score)
                valid_tweets += 1
            else:
                logger.error(f"Invalid tweet detected for miner {miner_key}. Blacklisting miner.")
                await self.miner_discovery_manager.set_miner_blacklisted(miner_key, True)
                return {"overall_score": 0.0}
            total_tweets += 1

            # Validate user account
            user_score = await self._validate_user(user_account)
            if user_score is not None:
                user_scores.append(user_score)
                valid_users += 1
            else:
                logger.error(f"Invalid user account detected for miner {miner_key}. Blacklisting miner.")
                await self.miner_discovery_manager.set_miner_blacklisted(miner_key, True)
                return {"overall_score": 0.0}
            total_users += 1

        # Calculate average scores
        avg_tweet_score = sum(tweet_scores) / len(tweet_scores) if tweet_scores else 0.0
        avg_user_score = sum(user_scores) / len(user_scores) if user_scores else 0.0

        # Smooth scoring
        tweet_contribution = self._smooth_score(valid_tweets, total_tweets)
        user_contribution = self._smooth_score(valid_users, total_users)

        # Final score (weighted combination)
        overall_score = (0.7 * tweet_contribution) + (0.3 * user_contribution)
        scores.update({
            "tweet_score": tweet_contribution,
            "user_score": user_contribution,
            "overall_score": overall_score
        })

        logger.info(f"Dataset scored: {scores}")
        return scores

    def _parse_and_normalize_date(self, date_value: str) -> datetime:
        """
        Parses a date string or datetime object and normalizes it to UTC.

        Args:
            date_value (str | datetime): The date value to parse.

        Returns:
            datetime: A timezone-aware UTC datetime object.
        """
        if isinstance(date_value, str):
            try:
                parsed_date = parser.isoparse(date_value)  # Parse ISO 8601
                if parsed_date.tzinfo is None:
                    parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                return parsed_date.astimezone(timezone.utc)
            except ValueError:
                raise ValueError(f"Invalid date string: {date_value}")
        elif isinstance(date_value, datetime):
            # Normalize to UTC
            if date_value.tzinfo is None:
                return date_value.replace(tzinfo=timezone.utc)
            return date_value.astimezone(timezone.utc)
        else:
            raise TypeError(f"Unsupported date format: {type(date_value)}")

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

            # Parse tweet_date safely and ensure it's a datetime object
            if isinstance(tweet_date, str):
                try:
                    tweet_date = parser.isoparse(tweet_date)
                except ValueError as e:
                    logger.warning(f"Failed to parse tweet_date '{tweet_date}': {e}")
                    return None
            elif not isinstance(tweet_date, datetime):
                logger.warning(f"Invalid tweet_date type: {type(tweet_date)}")
                return None

            # Ensure tweet_date is naive
            if tweet_date.tzinfo is not None:
                tweet_date = tweet_date.astimezone(timezone.utc).replace(tzinfo=None)

            # Check freshness (e.g., within the last 7 days)
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            days_old = (now - tweet_date).days
            freshness_factor = math.exp(-days_old / 7)  # Exponential decay for older tweets

            # Retrieve cached data
            cached_tweet = await self.tweet_cache_manager.get_tweet_cache(tweet_id)
            if cached_tweet:
                logger.info(f"Tweet data retrieved from cache for tweet_id {tweet_id}")
                return 1.0 * freshness_factor

            # Fetch live data if not cached
            fetched_tweet = self.twitter_service.get_tweet_details(tweet_id)
            if not fetched_tweet:
                logger.warning(f"Tweet not found for tweet_id {tweet_id}.")
                return None

            # Convert fetched_tweet.created_at to naive datetime
            created_at = parser.isoparse(fetched_tweet.created_at) if isinstance(fetched_tweet.created_at,
                                                                                 str) else fetched_tweet.created_at
            if created_at.tzinfo is not None:
                created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)

            await self.tweet_cache_manager.store_tweet_cache(
                tweet_id=tweet_id,
                tweet_date=created_at  # Always store as naive datetime
            )

            return 1.0 * freshness_factor

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

            # Retrieve cached data
            cached_user = await self.user_cache_manager.get_user_cache(user_id)
            if cached_user:
                logger.info(f"User data retrieved from cache for user_id {user_id}")
                return 1.0

            # Fetch live data if not cached
            fetched_user = self.twitter_service.get_user_details(user_id)
            if not fetched_user:
                logger.warning(f"User not found for user_id {user_id}.")
                return None

            await self.user_cache_manager.store_user_cache(
                user_id=user_id,
                follower_count=fetched_user.followers_count,
                verified=fetched_user.verified
            )

            return 1.0

        except Exception as e:
            logger.error(f"Error validating user: {e}")
            return None

    def _smooth_score(self, validated_entries: int, total_entries: int) -> float:
        """
        Calculate a smooth score using exponential growth with diminishing returns.

        Args:
            validated_entries (int): Number of valid entries.
            total_entries (int): Total number of entries.

        Returns:
            float: Smooth score between 0 and 1.
        """
        if total_entries == 0:
            return 0.0

        accuracy = validated_entries / total_entries
        return 1 - math.exp(-accuracy * 5)  # Exponential growth with diminishing returns

    async def validate_step(self, netuid: int, settings: ValidatorSettings) -> None:
        """
        Perform a single validation step, processing miners and scoring their datasets.
        """
        score_dict: Dict[int, float] = {}
        miners_module_info = {}

        # Get modules and their addresses
        modules = get_map_modules(self.client, netuid=netuid, include_balances=False)
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

            # Skip blacklisted miners
            if await self.miner_discovery_manager.is_miner_blacklisted(miner_key):
                logger.warning(f"Skipping blacklisted miner: {miner_key}")
                continue

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

            await self.miner_discovery_manager.update_miner_rank(miner_metadata['key'], miner_metadata['emission'])

            # Score dataset
            dataset = await Validator._fetch_and_validate_dataset(
                discovery.dataset_link, self.graph_handler, discovery.token, self.settings.ENABLE_GATEWAY
            )
            if not dataset:
                logger.warning(f"Invalid dataset for miner {miner_key}. Excluding from scoring.")
                continue

            scores = await self.score_dataset(dataset, miner_key)
            score_dict[uid] = scores.get("overall_score", 0.0)
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

    def set_weights(self, settings: ValidatorSettings, score_dict: Dict[int, float], netuid: int, client: CommuneClient, key: Keypair) -> None:
        """
        Calculate and set weights for miners based on their scores.
        """
        score_dict = cut_to_max_allowed_weights(score_dict, settings.MAX_ALLOWED_WEIGHTS)
        self.weights_storage.setup()
        weighted_scores: Dict[int, int] = dict()

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

    async def query_memgraph(self, token: str, query: str) -> dict:
        """
        Queries the Memgraph database using GraphSearch and returns the results.

        Args:
            token (str): The token associated with the query.
            query (str): The Cypher query to be executed.

        Returns:
            dict: A dictionary containing request metadata and query results.
        """
        request_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        query_hash = generate_hash(query)

        # Check if gateway is enabled
        if not self.settings.ENABLE_GATEWAY:
            error_message = "Gateway is disabled. Memgraph query functionality is not available."
            logger.error(error_message)
            return {
                "request_id": request_id,
                "timestamp": timestamp,
                "token": token,
                "query": query,
                "query_hash": query_hash,
                "response_time": None,
                "results": None,
                "error": error_message,
            }

        graph_search = GraphSearch(self.settings)

        try:
            # Execute the query using GraphSearch
            start_time = time.time()
            results = graph_search.execute_query(query)
            response_time = round(time.time() - start_time, 3)

            # Generate a response dictionary
            response = {
                "request_id": request_id,
                "timestamp": timestamp,
                "token": token,
                "query": query,
                "query_hash": query_hash,
                "response_time": response_time,
                "results": results,
            }
            return response
        except Exception as e:
            # Handle query execution errors
            logger.error(f"Error querying Memgraph: {e}")
            return {
                "request_id": request_id,
                "timestamp": timestamp,
                "token": token,
                "query": query,
                "query_hash": query_hash,
                "response_time": None,
                "results": None,
                "error": str(e),
            }
        finally:
            # Ensure the GraphSearch connection is closed
            graph_search.close()


