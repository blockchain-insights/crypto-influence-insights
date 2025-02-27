from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class Discovery(BaseModel):
    token: str = Field("PEPE", title="Token to scrape info for")
    version: float = Field(1.0, title="The version of the discovery")
    dataset_link: str = Field(..., title="A link to the miner dataset with scraped data")


class TwitterChallenge(BaseModel):
    token: str
    output: Optional[Dict[str, Optional[Any]]] = None


class TwitterChallengesResponse(BaseModel):
    token: str
    output: Dict[str, Optional[Any]]

class TwitterChallengeMinerResponse(BaseModel):
    token: str
    version: float
    graph_db: str
    challenge_response: TwitterChallengesResponse
    failed_challenges: int
