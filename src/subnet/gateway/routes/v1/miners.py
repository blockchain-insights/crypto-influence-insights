from typing import Optional
from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel
from src.subnet.validator.validator import Validator
from src.subnet.gateway import get_validator

miner_router = APIRouter(prefix="/v1/miner", tags=["miner"])


class MinerMetadataRequest(BaseModel):
    token: Optional[str] = None


@miner_router.get("/metadata")
async def get_metadata(token: Optional[str] = None,
                             validator: Validator = Depends(get_validator)):
    results = await validator.miner_discovery_manager.get_miners_by_token(token)
    return results

@miner_router.get("/miner/ranks")
async def get_ranks(network: Optional[str] = None,
                          validator: Validator = Depends(get_validator)):
    results = await validator.miner_discovery_manager.get_miners_for_leader_board(network)
    return results

@miner_router.get("/miner/networks")
async def get_miners_per_network(
                          validator: Validator = Depends(get_validator)):
    results = await validator.miner_discovery_manager.get_miners_per_token()
    return results
