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
from helpers.ipfs_utils import (
    upload_file_to_pinata,
    delete_old_snapshots,
    get_ipfs_link
    )
from keylimiter import TokenBucketLimiter
from loguru import logger
from starlette.middleware.cors import CORSMiddleware
from src.subnet import VERSION
from src.subnet.encryption import generate_hash
from src.subnet.miner._config import MinerSettings, load_environment
from src.subnet.miner.database.models.dataset_links import DatasetLinkManager
from src.subnet.miner.database.session_manager import DatabaseSessionManager
from src.subnet.miner.graph_search import GraphSearch
from src.subnet.protocol import TwitterChallenge
from substrateinterface import Keypair

class Miner(Module):
    def __init__(self, keypair: Keypair, settings: MinerSettings, dataset_link_manager: DatasetLinkManager):
        super().__init__()
        self.keypair = keypair
        self.settings = settings
        self.dataset_link_manager = dataset_link_manager

    @endpoint
    async def discovery(self, validator_version: str, validator_key: str) -> dict:
        """
        Returns the token, version, and dataset link of the miner.

        Returns:
            dict: Discovery information of the miner
            {
                "token": "PEPE",
                "version": "1.0",
                "dataset_link": "ipfs://<hash>"
            }
        """
        logger.debug(f"Received discovery request from {validator_key}", validator_key=validator_key)

        if float(validator_version) != VERSION:
            logger.error(f"Invalid validator version: {validator_version}, expected: {VERSION}")
            raise ValueError(f"Invalid validator version: {validator_version}, expected: {VERSION}")

        # Fetch the latest dataset link for the token
        try:
            dataset_link = await self.dataset_link_manager.get_latest_link(self.settings.TOKEN)
            if not dataset_link:
                logger.warning(f"No dataset link found for token: {self.settings.TOKEN}")
                dataset_link = "N/A"
        except Exception as e:
            logger.error(f"Failed to fetch dataset link: {e}")
            dataset_link = "Error fetching link"

        return {
            "token": self.settings.TOKEN,
            "version": VERSION,
            "dataset_link": dataset_link
        }

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
    session_manager = DatabaseSessionManager()
    session_manager.init(settings.DATABASE_URL)
    dataset_link_manager = DatasetLinkManager(session_manager)
    miner = Miner(keypair=keypair, settings=settings, dataset_link_manager=dataset_link_manager)
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
