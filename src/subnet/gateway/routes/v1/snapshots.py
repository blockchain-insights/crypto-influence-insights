from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.subnet.validator.validator import Validator
from src.subnet.gateway.services.snapshots_api import SnapshotService
from src.subnet.gateway.helpers.reponse_formatter import format_response, ResponseType
from src.subnet.gateway import get_validator

snapshot_router = APIRouter(prefix="/v1/snapshots", tags=["snapshots"])


@snapshot_router.get("/{token}/fetch-snapshot", summary="Fetch Snapshot", description="Fetch a snapshot for a specified token within a given date range.")
async def fetch_snapshot(
    token: str,
    from_date: str = Query(..., description="Start date for the snapshot (YYYY-MM-DD)"),
    to_date: str = Query(..., description="End date for the snapshot (YYYY-MM-DD)"),
    miner_key: Optional[str] = Query(None, description="Optional miner key for targeted query"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator),
):
    """
    Fetch a snapshot for a specified token within a given date range.
    """
    snapshot_service = SnapshotService(validator)

    try:
        data = await snapshot_service.get_snapshot(
            token=token,
            from_date=from_date,
            to_date=to_date,
            miner_key=miner_key,
        )
        return format_response(data, response_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch snapshot: {str(e)}")
