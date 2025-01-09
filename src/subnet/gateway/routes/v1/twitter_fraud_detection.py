from typing import Optional, List
from fastapi import Depends, APIRouter, Query, HTTPException
from pydantic import BaseModel

from src.subnet.validator.validator import Validator
from src.subnet.gateway.helpers.reponse_formatter import format_response, ResponseType
from src.subnet.gateway.services.twitter_fraud_detection_api import TwitterFraudDetectionApi
from src.subnet.gateway import get_validator

twitter_fraud_detection_router = APIRouter(prefix="/v1/twitter-fraud-detection", tags=["twitter-fraud-detection"])


@twitter_fraud_detection_router.get(
    "/{token}/get-engagement-trends",
    summary="Get User Engagement Trends",
    description="Analyze and retrieve daily engagement trends for a specified token over a given time period, optionally filtered by region."
)
async def get_user_engagement_trends(
    token: str,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze engagement trends"),
    region: str = Query(None, description="Filter engagement trends by region"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Analyze and retrieve daily engagement trends for a specified token over a given time period, optionally filtered by region.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_user_engagement_trends(token=token, days=days, region=region)

    return format_response(data, response_type)

@twitter_fraud_detection_router.get(
    "/{token}/detect-influencers",
    summary="Detect Influencers",
    description="Identify top influencers for a specified token based on follower count, engagement, and other criteria."
)
async def detect_influencers(
    token: str,
    min_follower_count: int = Query(1000, description="Minimum follower count to qualify as an influencer"),
    limit: int = Query(10, description="Number of top influencers to return"),
    time_period: int = Query(None, description="Time period (in days) to filter tweets"),
    min_tweet_count: int = Query(0, description="Minimum number of tweets to qualify as an influencer"),
    verified: bool = Query(None, description="Filter for verified influencers (true/false)"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Identify top influencers for a specified token based on follower count, engagement, and optional filters.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_influencers(
        token=token,
        min_follower_count=min_follower_count,
        limit=limit,
        time_period=time_period,
        min_tweet_count=min_tweet_count,
        verified=verified
    )
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
    "/{token}/fetch-account-analysis",
    summary="Fetch Account Analysis for Twitter Bot Content",
    description="Fetch account analysis, including patterns, influencers, anomalies, and suspicious accounts for Twitter bot content generation."
)
async def fetch_account_analysis(
    token: str,
    limit: int = Query(50, description="Number of records to return"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Fetch account analysis, including patterns, influencers, anomalies, and suspicious accounts.
    """
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.fetch_account_analysis(token=token, limit=limit)
    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{token}/real-time-scam-alerts", summary="Real-Time Scam Alerts", description="Retrieve tweets or users flagged as potential scams within a recent timeframe.")
async def real_time_scam_alerts(
    token: str,
    timeframe: str = Query("24h", description="Timeframe to analyze for scams, e.g., '24h' or '1d'."),
    limit: int = Query(100, description="Maximum number of results to return."),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Retrieve tweets or users flagged as potential scams within a recent timeframe.
    """
    # Create an instance of the service layer
    query_api = TwitterFraudDetectionApi(validator)

    # Fetch scam alerts using the service layer
    data = await query_api.get_real_time_scam_alerts(token=token, timeframe=timeframe, limit=limit)

    # Return the formatted response
    return format_response(data, response_type)


@twitter_fraud_detection_router.get(
    "/{token}/activity-snapshot",
    summary="Get Token Activity Snapshot",
    description="Retrieve aggregated activity data for a specific token, including daily or weekly mentions and associated tweets."
)
async def get_token_activity_snapshot(
    token: str,
    timeframe: str = Query("7d", description="Timeframe to analyze mentions (e.g., '1d', '7d')."),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    """
    Retrieve aggregated activity data for a specific token.

    Args:
        token (str): The token to analyze.
        timeframe (str): Timeframe for analysis (default: '7d').
        response_type (ResponseType): Response format (default: JSON).
        validator (Validator): Validator dependency.

    Returns:
        Formatted response containing aggregated activity data.
    """
    # Create an instance of the service layer
    query_api = TwitterFraudDetectionApi(validator)

    # Fetch activity snapshot using the service layer
    data = await query_api.get_token_activity_snapshot(token=token, timeframe=timeframe)

    # Return the formatted response
    return format_response(data, response_type)
