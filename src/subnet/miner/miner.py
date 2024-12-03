import signal
from datetime import datetime
from typing import Dict, Optional

from communex._common import get_node_url
from communex.client import CommuneClient
from communex.module import Module, endpoint
from communex.module._rate_limiters.limiters import IpLimiterParams
from helpers.file_utils import save_to_file
from helpers.cypher_utils import generate_cypher_from_results
from keylimiter import TokenBucketLimiter
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from src.subnet import VERSION
from src.subnet.miner._config import MinerSettings, load_environment
from src.subnet.miner.graph_search import GraphSearch
from src.subnet.protocol import TwitterChallenge



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
        challenge = TwitterChallenge(**challenge)

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

    @endpoint
    async def export_snapshot(self, token: str, from_date: str, to_date: str) -> dict:
        """
        Exports a snapshot of the database for a specific token and date range.
        Args:
            token (str): The token name to filter by.
            from_date (str): Start date for filtering (YYYY-MM-DD).
            to_date (str): End date for filtering (YYYY-MM-DD).

        Returns:
            dict: A downloadable link or raw Cypher export string.
        """
        try:
            # Adjusted query to include MENTIONS relationship
            query = f"""
                MATCH (t:Tweet)<-[:MENTIONED_IN]-(tok:Token {{name: '{token}'}})
                WHERE datetime(replace(t.timestamp, " ", "T")) >= datetime('{from_date}')
                  AND datetime(replace(t.timestamp, " ", "T")) <= datetime('{to_date}')
                OPTIONAL MATCH (u:UserAccount)-[:POSTED]->(t)
                OPTIONAL MATCH (u)-[:LOCATED_IN]->(r)
                OPTIONAL MATCH (u)-[:MENTIONS]->(tok)
                RETURN t, tok, u, r
            """

            # Execute the query
            results = self.graph_search.execute_query(query)

            # Generate Cypher export from results
            cypher_export = generate_cypher_from_results(results)

            # Save the generated Cypher to a file
            filename = f"snapshot_{token}_{from_date}_to_{to_date}.cypher"
            filepath = save_to_file(cypher_export, filename)

            # Return success response with download link
            return {"message": "Snapshot generated successfully", "download_link": filepath}
        except Exception as e:
            logger.error(f"Error generating snapshot: {str(e)}")
            return {"error": str(e)}


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
