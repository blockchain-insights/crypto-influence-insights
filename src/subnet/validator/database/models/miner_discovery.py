import random
from typing import Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, update, insert, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import delete
from datetime import datetime

from src.subnet.validator.database import OrmBase
from src.subnet.validator.database.base_model import to_dict
from src.subnet.validator.database.session_manager import DatabaseSessionManager

Base = declarative_base()


class MinerDiscovery(OrmBase):
    __tablename__ = 'miner_discoveries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    uid = Column(Integer, nullable=False)
    miner_key = Column(String, nullable=False, unique=True)
    miner_address = Column(String, nullable=False, default='0.0.0.0')
    miner_ip_port = Column(String, nullable=False, default='0')
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    token = Column(String, nullable=False)
    rank = Column(Float, nullable=False, default=0.0)
    version = Column(Float, nullable=False, default=1.0)
    ipfs_link = Column(String, nullable=False)
    blacklisted = Column(Integer, nullable=False, default=0)  # 0 = not blacklisted, 1 = blacklisted


class MinerDiscoveryManager:
    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager

    async def store_miner_metadata(self, uid: int, miner_key: str, miner_address: str, miner_ip_port: str, token: str, version: float, ipfs_link: str):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = insert(MinerDiscovery).values(
                    uid=uid,
                    miner_key=miner_key,
                    miner_address=miner_address,
                    miner_ip_port=miner_ip_port,
                    token=token,
                    timestamp=datetime.utcnow(),
                    version=version,
                    ipfs_link=ipfs_link
                ).on_conflict_do_update(
                    index_elements=['miner_key'],
                    set_={
                        'uid': uid,
                        'miner_address': miner_address,
                        'miner_ip_port': miner_ip_port,
                        'token': token,
                        'version': version,
                        'ipfs_link': ipfs_link,
                        'timestamp': datetime.utcnow()
                    }
                )
                await session.execute(stmt)

    async def get_miner_by_key(self, miner_key: str, token: str):
        async with self.session_manager.session() as session:
            result = await session.execute(
                select(MinerDiscovery).where(MinerDiscovery.miner_key == miner_key, MinerDiscovery.token == token)
            )
            miner = result.scalars().first()
            if miner is None:
                return None
            return to_dict(miner)

    async def get_miners_per_token(self):
        async with self.session_manager.session() as session:
            result = await session.execute(
                select(
                    MinerDiscovery.token,
                    func.count(MinerDiscovery.id).label('count')
                )
                .where(MinerDiscovery.blacklisted == 0)
                .group_by(MinerDiscovery.token)
                .order_by(func.count(MinerDiscovery.id).desc())
            )

            rows = result.fetchall()

            return [{'token': row.token, 'count': row.count} for row in rows]

    async def get_miners_by_token(self, token: Optional[str]):
        async with self.session_manager.session() as session:
            if not token:
                result = await session.execute(
                    select(MinerDiscovery)
                    .where(MinerDiscovery.blacklisted == 0)
                    .order_by(MinerDiscovery.timestamp, MinerDiscovery.rank)
                )
                return [to_dict(result) for result in result.scalars().all()]
            else:
                result = await session.execute(
                    select(MinerDiscovery)
                    .where(MinerDiscovery.token == token)
                    .order_by(MinerDiscovery.timestamp, MinerDiscovery.rank)
                )
                return [to_dict(result) for result in result.scalars().all()]

    async def update_miner_rank(self, miner_key: str, new_rank: float):
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = update(MinerDiscovery).where(
                    MinerDiscovery.miner_key == miner_key
                ).values(rank=new_rank)
                await session.execute(stmt)

    async def remove_all_records(self):
        async with self.session_manager.session() as session:
            async with session.begin():
                await session.execute(delete(MinerDiscovery))

    async def remove_miner_by_key(self, miner_key: str):
        async with self.session_manager.session() as session:
            async with session.begin():
                await session.execute(
                    delete(MinerDiscovery).where(MinerDiscovery.miner_key == miner_key)
                )

    async def get_miners_for_leader_board(self, token: Optional[str] = None):
        async with self.session_manager.session() as session:
            if not token:
                # Raw SQL query without token filter
                raw_sql = """
                SELECT 
                    md.token,
                    md.miner_key,
                    CAST(md.timestamp AS VARCHAR) AS timestamp,
                    md.rank,
                    md.ipfs_link
                FROM 
                    miner_discoveries AS md
                WHERE
                    md.blacklisted = 0
                ORDER BY 
                    md.timestamp DESC, 
                    md.rank DESC;
                """
            else:
                # Raw SQL query with token filter
                raw_sql = """
                SELECT 
                    md.id,
                    md.token,
                    CAST(md.timestamp AS VARCHAR) AS timestamp,
                    md.rank,
                    md.ipfs_link
                FROM 
                    miner_discoveries AS md
                WHERE 
                    md.token = :token
                ORDER BY 
                    md.timestamp DESC, 
                    md.rank DESC;
                """

            # Execute raw SQL query
            result = await session.execute(text(raw_sql), {"token": token} if token else {})
            # Use row._mapping to convert each row to a dictionary
            miners = [dict(row._mapping) for row in result.fetchall()]

            if not token:
                tokens = set(miner['token'] for miner in miners)
                return [
                    {
                        "token": tok,
                        "data": [miner for miner in miners if miner['token'] == tok]
                    }
                    for tok in tokens
                ]
            else:
                return {"token": token, "data": miners}

    async def set_miner_blacklisted(self, miner_key: str, blacklisted: bool):
        """
        Set the blacklisted flag for a miner.

        Args:
            miner_key (str): The key of the miner.
            blacklisted (bool): True to blacklist the miner, False to unblacklist.
        """
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = update(MinerDiscovery).where(
                    MinerDiscovery.miner_key == miner_key
                ).values(blacklisted=1 if blacklisted else 0)
                await session.execute(stmt)

    async def is_miner_blacklisted(self, miner_key: str) -> bool:
        """
        Check if a miner is blacklisted.

        Args:
            miner_key (str): The key of the miner.

        Returns:
            bool: True if the miner is blacklisted, False otherwise.
        """
        async with self.session_manager.session() as session:
            result = await session.execute(
                select(MinerDiscovery.blacklisted).where(MinerDiscovery.miner_key == miner_key)
            )
            blacklisted = result.scalar()
            return blacklisted == 1
