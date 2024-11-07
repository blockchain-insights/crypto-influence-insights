import signal
from datetime import datetime
from typing import Dict, Optional

from communex._common import get_node_url
from communex.client import CommuneClient
from communex.module import Module, endpoint
from communex.module._rate_limiters.limiters import IpLimiterParams
from keylimiter import TokenBucketLimiter
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from src.subnet import VERSION
from src.subnet.miner._config import MinerSettings, load_environment
from src.subnet.miner import GraphSearch
from src.subnet.protocol import TwitterChallenge, MODEL_KIND_FUNDS_FLOW, MODEL_KIND_BALANCE_TRACKING
from src.subnet.validator.database import db_manager


class Miner(Module):

    def __init__(self, settings: MinerSettings):
        super().__init__()
        self.settings = settings
        self.graph_search = GraphSearch(settings)

    @endpoint
    async def discovery(self, validator_version: str, validator_key: str) -> dict:
        """
        Returns the token, version and graph database type of the miner
        Returns:
            dict: The tokens of the miner
            {
                "token": "PEPE",
                "version": 1.0,
                "graph_db": "neo4j"
            }
        """

        logger.debug(f"Received discovery request from {validator_key}", validator_key=validator_key)

        if float(validator_version) != VERSION:
            logger.error(f"Invalid validator version: {validator_version}, expected: {VERSION}")
            raise ValueError(f"Invalid validator version: {validator_version}, expected: {VERSION}")

        return {
            "token": self.settings.TOKEN,
            "version": VERSION,
            "graph_db": self.settings.GRAPH_DB_TYPE
        }

    @endpoint
    async def query(self, query: str, validator_key: str) -> dict:

        logger.debug(f"Received challenge request from {validator_key}", validator_key=validator_key)

        try:
            result = self.graph_search.execute_query(query)
            return result
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {"error": str(e)}

    from typing import Dict

    @endpoint
    async def challenge(self, challenge: TwitterChallenge, validator_key: str) -> TwitterChallenge:
        """
        Solves the Twitter verification challenge and returns the output.

        Args:
            validator_key: The key of the requesting validator.
            challenge: {
                "token": "PEPE"
            }

        Returns:
            TwitterChallenge with output details:
            {
                "output": {
                    "tweet_id": "1851010642079096862",
                    "user_id": "3022633321",
                    "follower_count": 6455,
                    "tweet_date": "2024-11-01T12:34:56Z",
                    "verified": False
                }
            }
        """

        logger.debug(f"Received Twitter verification challenge from {validator_key}", validator_key=validator_key)

        # Instantiate the challenge object based on the provided token
        challenge = TwitterChallenge(**challenge.dict())

        # Use the Twitter-specific search function to retrieve tweet data
        tweet_data: Dict[str, Optional[str]] = self.graph_search.solve_twitter_challenge(token=challenge.token)

        if tweet_data:
            challenge.output = tweet_data
            logger.info(f"Challenge solved successfully for token {challenge.token}")
        else:
            challenge.output = {"error": "No matching tweet or user found for the token"}
            logger.warning(
                f"No matching tweet or user found for the Twitter verification challenge with token {challenge.token}")

        return challenge

if __name__ == "__main__":
    from communex.module.server import ModuleServer
    from communex.compat.key import classic_load_key
    import uvicorn
    import time
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m subnet.cli <environment> ; where <environment> is 'testnet' or 'mainnet'")
        sys.exit(1)

    env = sys.argv[1]
    use_testnet = env == 'testnet'
    load_environment(env)

    settings = MinerSettings()
    keypair = classic_load_key(settings.MINER_KEY)

    def patch_record(record):
        record["extra"]["miner_key"] = keypair.ss58_address
        record["extra"]["service"] = 'miner'
        record["extra"]["timestamp"] = datetime.utcnow().isoformat()
        record["extra"]["level"] = record['level'].name

        return True

    logger.remove()
    logger.add(
        "../logs/miner.log",
        rotation="500 MB",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}",
        filter=patch_record
    )

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <blue>{message}</blue> | {extra}",
        level="DEBUG",
        filter = patch_record
    )

    c_client = CommuneClient(get_node_url(use_testnet=use_testnet))
    miner = Miner(settings=settings)
    refill_rate: float = 1 / 1000
    bucket = TokenBucketLimiter(
        refill_rate=refill_rate,
        bucket_size=1000,
        time_func=time.time,
    )
    limiter = IpLimiterParams()
    db_manager.init(settings.DATABASE_URL)

    server = ModuleServer(miner,
                          keypair,
                          subnets_whitelist=[settings.NET_UID],
                          use_testnet=use_testnet,
                          limiter=limiter)

    app = server.get_fastapi_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def shutdown_handler(signal, frame):
        uvicorn_server.should_exit = True
        uvicorn_server.force_exit = True

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    uvicorn_server = uvicorn.Server(config=uvicorn.Config(app, host="0.0.0.0", port=settings.PORT, workers=settings.WORKERS))
    uvicorn_server.run()
