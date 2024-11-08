from typing import Optional, Dict
from sqlalchemy import Column, String, DateTime, BigInteger, Boolean, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from src.subnet.validator.database import OrmBase
from src.subnet.validator.database.session_manager import DatabaseSessionManager

Base = declarative_base()

# Entity for Tweet Cache
class TweetCache(OrmBase):
    __tablename__ = 'tweet_cache'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tweet_id = Column(String, nullable=False, unique=True)
    tweet_date = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint('tweet_id', name='uq_tweet_id'),
    )

# Manager for Tweet Cache
class TweetCacheManager:
    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager

    async def store_tweet_cache(self, tweet_id: str, tweet_date: datetime):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = insert(TweetCache).values(
                    tweet_id=tweet_id,
                    tweet_date=tweet_date
                ).on_conflict_do_update(
                    index_elements=['tweet_id'],
                    set_={'tweet_date': tweet_date}
                )
                await session.execute(stmt)

    async def get_tweet_cache(self, tweet_id: str) -> Optional[Dict[str, Optional[str]]]:
        async with self.session_manager.session() as session:
            result = await session.execute(
                select(TweetCache).where(TweetCache.tweet_id == tweet_id)
            )
            record = result.scalars().first()
            if record:
                return {
                    "tweet_id": record.tweet_id,
                    "tweet_date": record.tweet_date.isoformat()
                }
            return None