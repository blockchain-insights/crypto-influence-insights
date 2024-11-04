from typing import Optional, Dict
from pydantic import BaseModel, Field

class Discovery(BaseModel):
    tokens: str = Field("PEPE", title="Tokens to scrape infor for")
    version: float = Field(1.0, title="The version of the discovery")
    graph_db: str = Field("neo4j", title="The graph database type")

class TwitterChallenge(BaseModel):
    token: str
    tweet_id: Optional[str] = None
    user_id: Optional[str] = None
    engagement_score: Optional[int] = None
    tweet_date: Optional[str] = None
    follower_count: Optional[int] = None
    verified: Optional[bool] = None
    output: Optional[Dict] = None


class ChallengesResponse(BaseModel):
    twitter_challenge_expected: str
    balance_tracking_challenge_expected: int
    funds_flow_challenge_actual: Optional[str]
    balance_tracking_challenge_actual: Optional[int]


class ChallengeMinerResponse(BaseModel):
    network: str
    version: float
    graph_db: str

    funds_flow_challenge_expected: str
    balance_tracking_challenge_expected: int
    funds_flow_challenge_actual: Optional[str]
    balance_tracking_challenge_actual: Optional[int]

    def get_failed_challenges(self):
        funds_flow_challenge_passed = self.funds_flow_challenge_expected == self.funds_flow_challenge_actual
        balance_tracking_challenge_passed = self.balance_tracking_challenge_expected == self.balance_tracking_challenge_actual

        failed_challenges = 0
        if funds_flow_challenge_passed is False:
            failed_challenges += 1

        if balance_tracking_challenge_passed is False:
            failed_challenges += 1

        return failed_challenges
