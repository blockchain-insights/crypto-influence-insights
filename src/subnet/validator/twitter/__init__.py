from itertools import cycle
import requests
from loguru import logger
from pydantic import BaseModel
from ratelimit import limits, sleep_and_retry
from typing import Optional
from src.subnet.validator._config import ValidatorSettings

class RoundRobinBearerTokenProvider:
    def __init__(self, settings: ValidatorSettings):
        self.tokens = settings.TWITTER_BEARER_TOKENS.split(";")
        self.tokens_cycle = cycle(self.tokens)

    def get_token(self):
        return next(self.tokens_cycle)


class TwitterClient:
    def __init__(self, token_provider: RoundRobinBearerTokenProvider):
        self.token_provider = token_provider

    def create_headers(self):
        bearer_token = self.token_provider.get_token()
        return {"Authorization": f"Bearer {bearer_token}"}

    @sleep_and_retry
    @limits(calls=15, period=15 * 60)
    def get_user(self, user_id: str) -> Optional[dict]:
        url = f"https://api.twitter.com/2/users/{user_id}"
        params = {
            "user.fields": "id,username,verified,public_metrics,description"
        }
        headers = self.create_headers()
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            logger.error(f"get_user: Request error {response.status_code} {response.text}")
            return None
        return response.json().get("data")

    @sleep_and_retry
    @limits(calls=15, period=15 * 60)
    def get_tweet_details(self, tweet_id: str) -> Optional[dict]:
        url = f"https://api.twitter.com/2/tweets/{tweet_id}"
        params = {
            "tweet.fields": "created_at,author_id,public_metrics,text",
            "expansions": "author_id"
        }
        headers = self.create_headers()
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            logger.error(f"get_tweet_details: Request error {response.status_code} {response.text}")
            return None
        return response.json().get("data")


class TwitterService:
    def __init__(self, twitter_client: TwitterClient):
        self.twitter_client = twitter_client

    def get_user_details(self, user_id: str) -> Optional['TwitterUser']:
        raw_data = self.twitter_client.get_user(user_id)
        if raw_data:
            return TwitterUser(
                user_id=raw_data["id"],
                user_name=raw_data["username"],
                verified=raw_data["verified"],
                followers_count=raw_data["public_metrics"]["followers_count"],
                description=raw_data["description"]
            )
        return None

    def get_tweet_details(self, tweet_id: str) -> Optional['Tweet']:
        raw_data = self.twitter_client.get_tweet_details(tweet_id)
        if raw_data:
            return Tweet(
                tweet_id=raw_data["id"],
                created_at=raw_data["created_at"],
                text=raw_data["text"],
                user_id=raw_data["author_id"]
            )
        return None


class TwitterUser(BaseModel):
    user_id: str
    user_name: str
    verified: bool
    followers_count: int
    description: str


class Tweet(BaseModel):
    tweet_id: str
    created_at: str
    text: str
    user_id: str
