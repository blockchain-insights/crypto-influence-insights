import asyncio
import signal
import sys
from datetime import datetime
from aioredis import Redis
from communex._common import get_node_url
from communex.client import CommuneClient
from communex.compat.key import classic_load_key
from loguru import logger
from substrateinterface import Keypair

from src.subnet.validator.database.models.miner_discovery import MinerDiscoveryManager
from src.subnet.validator.database.models.tweet_cache import TweetCacheManager
from src.subnet.validator.database.models.user_cache import UserCacheManager
from src.subnet.validator.database.session_manager import DatabaseSessionManager, run_migrations
from src.subnet.validator.weights_storage import WeightsStorage
from src.subnet.validator._config import load_environment, SettingsManager
from src.subnet.validator.validator import Validator
from src.subnet.validator.helpers.validator_graph_handler import ValidatorGraphHandler
from validator.twitter import TwitterClient, TwitterService, RoundRobinBearerTokenProvider


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python -m subnet.cli <environment>")
        sys.exit(1)

    environment = sys.argv[1]
    load_environment(environment)

    settings_manager = SettingsManager.get_instance()
    settings = settings_manager.get_settings()

    if settings.VALIDATOR_KEY is None:
        keypair = Keypair.create_from_private_key(settings.VALIDATOR_PRIVATE_KEY, ss58_format=42)
    elif settings.VALIDATOR_PRIVATE_KEY is None:
        keypair = classic_load_key(settings.VALIDATOR_KEY)
    else:
        logger.error("Both VALIDATOR_KEY and VALIDATOR_PRIVATE_KEY are set, only one should be set")
        sys.exit(1)


    def patch_record(record):
        record["extra"]["validator_key"] = keypair.ss58_address
        record["extra"]["service"] = 'validator'
        record["extra"]["timestamp"] = datetime.utcnow().isoformat()
        record["extra"]["level"] = record['level'].name

        return True

    logger.remove()
    logger.add(
        "../logs/validator.log",
        rotation="500 MB",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}",
        level="DEBUG",
        filter=patch_record
    )

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <blue>{message}</blue> | {extra}",
        level="DEBUG",
        filter=patch_record,
    )

    c_client = CommuneClient(get_node_url(use_testnet=(environment == 'testnet')))
    weights_storage = WeightsStorage(settings.WEIGHTS_FILE_NAME)

    session_manager = DatabaseSessionManager()
    session_manager.init(settings.DATABASE_URL)

    run_migrations()

    miner_discovery_manager = MinerDiscoveryManager(session_manager)
    tweet_cache_manager = TweetCacheManager(session_manager)
    user_cache_manager = UserCacheManager(session_manager)
    twitter_round_robbin_token_provider = RoundRobinBearerTokenProvider(settings)
    twitter_client = TwitterClient(twitter_round_robbin_token_provider)
    twitter_service = TwitterService(twitter_client)
    graph_handler = ValidatorGraphHandler(settings)

    redis_client = Redis.from_url(settings.REDIS_URL)

    validator = Validator(
        keypair,
        settings.NET_UID,
        c_client,
        weights_storage,
        miner_discovery_manager,
        tweet_cache_manager,
        user_cache_manager,
        twitter_service,
        graph_handler,
        redis_client,
        settings
    )


    def shutdown_handler(signal_num, frame):
        logger.info("Received shutdown signal, stopping...")
        validator.terminate_event.set()
        settings_manager.stop_reloader()
        logger.debug("Shutdown handler finished")

    # Signal handling for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        asyncio.run(validator.validation_loop(settings))
    except KeyboardInterrupt:
        logger.info("Validator loop interrupted")


