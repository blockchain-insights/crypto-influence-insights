import json
import os
import signal
from datetime import datetime
from typing import Dict, Optional

from communex._common import get_node_url
from communex.client import CommuneClient
from communex.module import Module, endpoint
from communex.module._rate_limiters.limiters import IpLimiterParams
from helpers.file_utils import save_to_file
from helpers.ipfs_utils import upload_file_to_pinata, get_ipfs_link
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
    async def export_snapshot(self, miner_key: str, token: str, from_date: str, to_date: str) -> dict:
        """
        Exports a snapshot of data, uploads it to Pinata, and returns the file's IPFS link.

        Args:
            miner_key (str): Unique identifier for the miner.
            token (str): The token for which data is exported.
            from_date (str): Start date for the snapshot.
            to_date (str): End date for the snapshot.

        Returns:
            dict: Response containing the file's CID and IPFS link.
        """
        try:
            # Properly formatted Cypher query
            query = f"""
            MATCH (t:Tweet)<-[mentioned_in:MENTIONED_IN]-(tok:Token {{name: '{token}'}})
            WHERE datetime(replace(t.timestamp, ' ', 'T')) >= datetime('{from_date}')
              AND datetime(replace(t.timestamp, ' ', 'T')) <= datetime('{to_date}')
            OPTIONAL MATCH (u:UserAccount)-[posted:POSTED]->(t)
            OPTIONAL MATCH (u)-[located_in:LOCATED_IN]->(r)
            OPTIONAL MATCH (u)-[mentions:MENTIONS]->(tok)
            RETURN t, tok, u, r, mentioned_in, posted, located_in, mentions
            """

            # APOC export query with streaming enabled
            apoc_query = f"""
            CALL apoc.export.cypher.query(
                "{query}",
                null,
                {{
                    format: "cypher",
                    cypherFormat: "create",
                    stream: true
                }}
            ) YIELD cypherStatements
            RETURN cypherStatements
            """

            # Execute the query and get the stream of Cypher statements
            result = self.graph_search.execute_query(apoc_query)

            if not isinstance(result, list):
                return {"error": "Unexpected response format from query"}

            # Filter and clean the Cypher statements from the stream
            cleaned_statements = "\n".join(
                line for item in result
                for line in item.get("cypherStatements", "").splitlines()
                if not line.strip().upper().startswith(("BEGIN", "COMMIT", "SCHEMA"))
            )

            if not cleaned_statements:
                return {"error": "No valid Cypher statements found in the response"}

            # Generate the filename with timestamp
            current_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_name = f"snapshot_{token}_{from_date}_to_{to_date}_{current_timestamp}.cypher"

            # Upload the file to Pinata
            upload_response = upload_file_to_pinata(cleaned_statements, file_name, miner_key, settings)

            if "error" in upload_response:
                return {"error": upload_response["error"]}

            file_cid = upload_response.get("IpfsHash")
            if not file_cid:
                return {"error": "Failed to retrieve CID for the snapshot"}

            # Generate a public IPFS link for the file
            file_link = get_ipfs_link(file_cid)

            # Return success response with file details
            return {
                "message": "Snapshot uploaded to IPFS successfully",
                "data": {
                    "file_name": file_name,
                    "file_cid": file_cid,
                    "file_link": file_link,
                },
            }

        except Exception as e:
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
