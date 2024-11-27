from typing import Optional, List
from fastapi import Depends, APIRouter, Query, HTTPException
from pydantic import BaseModel

from src.subnet.validator.validator import Validator
from src.subnet.validator_api.helpers.reponse_formatter import format_response, ResponseType
from src.subnet.validator_api.services.twitter_fraud_detection_api import TwitterFraudDetectionApi
from src.subnet.validator_api import get_validator

twitter_fraud_detection_router = APIRouter(prefix="/v1/twitter-fraud-detection", tags=["twitter-fraud-detection"])


@twitter_fraud_detection_router.get("/{token}/get-engagement-trends", summary="Get User Engagement Trends", description="Analyze and retrieve daily engagement trends for a specified token over a given time period.")
async def get_user_engagement_trends(
    token: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze engagement trends"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Analyze and retrieve daily engagement trends for a specified token over a given time period.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_user_engagement_trends(token=token, days=days)

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{token}/detect-influencers", summary="Detect Influencers", description="Identify top influencers for a specified token based on follower count and engagement.")
async def detect_influencers(
    token: str,
    min_follower_count: int = Query(1000, description="Minimum follower count to qualify as an influencer"),
    limit: int = Query(10, description="Number of top influencers to return"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Identify top influencers for a specified token based on follower count and engagement.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_influencers(token=token, min_follower_count=min_follower_count, limit=limit)

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{token}/detect-similarity", summary="Detect User Similarity", description="Find users with similar activity or engagement patterns for a specified token based on a similarity threshold.")
async def detect_similarity(
    token: str,
    similarity_threshold: float = Query(0.7, description="Threshold for similarity detection (0.0 to 1.0)"),
    type: str = Query("activity-based", regex="^(activity-based|engagement-based)$", description="Type of similarity analysis: activity-based or engagement-based"),
    limit: int = Query(10, description="Number of similar users to return"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Find users with similar activity or engagement patterns for a specified token based on a similarity threshold.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_similarity(
        token=token,
        similarity_threshold=similarity_threshold,
        similarity_type=type,
        limit=limit
    )

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{token}/detect-scam-mentions", summary="Detect Scam Mentions", description="Identify tweets or users potentially involved in scams mentioning the specified token.")
async def detect_scam_mentions(
    token: str,
    timeframe: str = Query("24h", description="Timeframe to analyze mentions (e.g., 24h, 7d)."),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Identify tweets or users potentially involved in scams mentioning the specified token.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_scam_mentions(token=token, timeframe=timeframe)

    return format_response(data, response_type)


@twitter_fraud_detection_router.post("/{token}/detect-anomalies", summary="Detect Anomalies", description="Find anomalies in user activity or engagement for the specified token.")
async def detect_anomalies(
    token: str,
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Find anomalies in user activity or engagement for the specified token.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_anomalies(token=token)

    return format_response(data, response_type)

@twitter_fraud_detection_router.get(
    "/{token}/fetch-insightful-data",
    summary="Fetch Insightful Data for Tweet Generation",
    description="Fetch patterns, influencers, and anomalies for insightful Twitter bot content."
)
async def fetch_insightful_data(
    token: str,
    limit: int = Query(50, description="Number of records to return"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Fetch patterns, influencers, and anomalies for insightful Twitter bot content.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.fetch_insightful_data(token=token, limit=limit)
    return format_response(data, response_type)


@twitter_fraud_detection_router.get(
    "/{token}/fetch-suspicious-accounts",
    summary="Fetch Suspicious Accounts",
    description="Fetch suspicious accounts with potentially unusual behaviors for Twitter bot analysis."
)
async def fetch_suspicious_accounts(
    token: str,
    limit: int = Query(50, description="Number of records to return"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Fetch suspicious accounts with potentially unusual behaviors for Twitter bot analysis.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.fetch_suspicious_accounts(token=token, limit=limit)
    return format_response(data, response_type)
