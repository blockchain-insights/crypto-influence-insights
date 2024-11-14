from typing import Optional, List
from fastapi import Depends, APIRouter, Query, HTTPException
from pydantic import BaseModel

from src.subnet.validator.validator import Validator
from src.subnet.validator_api.helpers.reponse_formatter import format_response, ResponseType
from src.subnet.validator_api.services.twitter_fraud_detection_api import TwitterFraudDetectionApi
from src.subnet.validator_api import get_validator

twitter_fraud_detection_router = APIRouter(prefix="/v1/twitter-fraud-detection", tags=["twitter-fraud-detection"])


@twitter_fraud_detection_router.get("/{token}/get-engagement-trends")
async def get_user_engagement_trends(
    token: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze engagement trends"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Retrieves user engagement trends for a specified token over a given time period.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_user_engagement_trends(token=token, days=days)

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{token}/detect-influencers")
async def detect_influencers(
    token: str,
    min_follower_count: int = Query(1000, description="Minimum follower count to qualify as an influencer"),
    limit: int = Query(10, description="Number of top influencers to return"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_influencers(token=token, min_follower_count=min_follower_count, limit=limit)

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{token}/detect-similarity")
async def detect_similarity(
    token: str,
    similarity_threshold: float = Query(0.7),
    type: str = Query("activity-based", regex="^(activity-based|engagement-based)$"),
    limit: int = Query(10),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_similarity(
        token=token,
        similarity_threshold=similarity_threshold,
        similarity_type=type,
        limit=limit
    )

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{token}/detect-scam-mentions")
async def detect_scam_mentions(
    token: str,
    timeframe: str = Query("24h"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_scam_mentions(token=token, timeframe=timeframe)

    return format_response(data, response_type)


@twitter_fraud_detection_router.post("/{token}/detect-anomalies")
async def detect_anomalies(
    token: str,
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_anomalies(token=token)

    return format_response(data, response_type)