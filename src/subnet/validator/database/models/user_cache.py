from typing import Optional, Dict
from sqlalchemy import Column, String, DateTime, BigInteger, Boolean, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from src.subnet.validator.database import OrmBase
from src.subnet.validator.database.session_manager import DatabaseSessionManager

Base = declarative_base()
# Entity for User Cache
class UserCache(OrmBase):
    __tablename__ = 'user_cache'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, unique=True)
    follower_count = Column(BigInteger, nullable=True)
    verified = Column(Boolean, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_id'),
    )
# Manager for User Cache
class UserCacheManager:
    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager

    async def store_user_cache(self, user_id: str, follower_count: int, verified: bool):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = insert(UserCache).values(
                    user_id=user_id,
                    follower_count=follower_count,
                    verified=verified
                ).on_conflict_do_update(
                    index_elements=['user_id'],
                    set_={
                        'follower_count': follower_count,
                        'verified': verified
                    }
                )
                await session.execute(stmt)

    async def get_user_cache(self, user_id: str) -> Optional[Dict[str, Optional[str]]]:
        async with self.session_manager.session() as session:
            result = await session.execute(
                select(UserCache).where(UserCache.user_id == user_id)
            )
            record = result.scalars().first()
            if record:
                return {
                    "user_id": record.user_id,
                    "follower_count": str(record.follower_count),
                    "verified": record.verified
                }
            return None
