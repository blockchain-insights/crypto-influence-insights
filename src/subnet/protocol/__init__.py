from typing import Optional, Dict
from pydantic import BaseModel, Field


class Discovery(BaseModel):
    token: str = Field("PEPE", title="Token to scrape info for")
    version: float = Field(1.0, title="The version of the discovery")
    graph_db: str = Field("neo4j", title="The graph database type")


class TwitterChallenge(BaseModel):
    token: str
    output: Optional[Dict[str, Optional[str]]] = None


class TwitterChallengesResponse(BaseModel):
    token: str
    output: Dict[str, Optional[str]]

class TwitterChallengeMinerResponse(BaseModel):
    token: str
    version: float
    graph_db: str
    challenge_response: TwitterChallengesResponse
    failed_challenges: int

    def get_failed_challenges(self, expected_output: Dict[str, Optional[str]]) -> int:
        return self.failed_challenges
