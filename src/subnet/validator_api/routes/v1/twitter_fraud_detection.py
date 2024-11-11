from typing import Optional, List
from fastapi import Depends, APIRouter, Query, HTTPException
from pydantic import BaseModel

from src.subnet.validator.validator import Validator
from src.subnet.validator_api import get_validator, api_key_auth
from src.subnet.validator_api.helpers.reponse_formatter import format_response, ResponseType
from src.subnet.validator_api.services.twitter_fraud_detection_api import TwitterFraudDetectionApi

twitter_fraud_detection_router = APIRouter(prefix="/v1/twitter-fraud-detection", tags=["twitter-fraud-detection"])


@twitter_fraud_detection_router.get("/{network}/detect-communities")
async def detect_communities(
    network: str,
    min_size: int = Query(3),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator),
    api_key: str = Depends(api_key_auth),
):

    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_communities(min_size=min_size)

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{network}/detect-influencers")
async def detect_influencers(
    network: str,
    threshold: float = Query(0.1),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator),
    api_key: str = Depends(api_key_auth),
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_influencers(threshold=threshold)

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{network}/detect-similarity")
async def detect_similarity(
    network: str,
    similarity_threshold: float = Query(0.7),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator),
    api_key: str = Depends(api_key_auth),
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_similarity(similarity_threshold=similarity_threshold)

    return format_response(data, response_type)


@twitter_fraud_detection_router.get("/{network}/detect-scam-mentions")
async def detect_scam_mentions(
    network: str,
    token: str,
    timeframe: str = Query("24h"),
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator),
    api_key: str = Depends(api_key_auth),
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_scam_mentions(token=token, timeframe=timeframe)

    return format_response(data, response_type)


@twitter_fraud_detection_router.post("/{network}/detect-anomalies")
async def detect_anomalies(
    network: str,
    response_type: ResponseType = Query(ResponseType.json),
    validator: Validator = Depends(get_validator),
    api_key: str = Depends(api_key_auth),
):
    query_api = TwitterFraudDetectionApi(validator)
    data = await query_api.get_anomalies()

    return format_response(data, response_type)