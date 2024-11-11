from typing import Optional, List
from fastapi import Depends, APIRouter, Query, HTTPException
from pydantic import BaseModel

from src.subnet.validator.validator import Validator
from src.subnet.validator_api.helpers.reponse_formatter import format_response, ResponseType
from src.subnet.validator_api.services.twitter_fraud_detection_api import TwitterFraudDetectionApi
from src.subnet.validator_api import get_validator

twitter_fraud_detection_router = APIRouter(prefix="/v1/twitter-fraud-detection", tags=["twitter-fraud-detection"])


@twitter_fraud_detection_router.get("/{token}/detect-communities")
async def detect_communities(
    token: str,
    min_size: int = Query(3),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):

    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_communities(token=token, min_size=min_size)

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{token}/detect-influencers")
async def detect_influencers(
    token: str,
    threshold: float = Query(0.1),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_influencers(token=token, threshold=threshold)

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{token}/detect-similarity")
async def detect_similarity(
    token: str,
    similarity_threshold: float = Query(0.7),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator)
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_similarity(token=token, similarity_threshold=similarity_threshold)

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