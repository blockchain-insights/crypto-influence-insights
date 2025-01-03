from sqlalchemy import Column, String, DateTime, select
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from src.subnet.miner.database import OrmBase

Base = declarative_base()

class DatasetLink(OrmBase):
    """
    Model representing the dataset link table.
    This table stores the latest dataset links for each token dataset.
    """
    __tablename__ = 'dataset_links'
    token = Column(String, primary_key=True)  # Unique token identifier, acts as the primary key
    ipfs_link = Column(String, nullable=False)  # Latest IPFS link to the dataset
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)  # Timestamp for the update

class DatasetLinkManager:
    """
    Manager class for handling operations on the dataset link table.
    """
    def __init__(self, session_manager):
        self.session_manager = session_manager

    async def store_latest_link(self, token: str, ipfs_link: str):
        """
        Store or update the latest IPFS link for a specific token.

        Args:
            token (str): The token identifier.
            ipfs_link (str): The latest IPFS link to the dataset.
        """
        async with self.session_manager.session() as session:
            async with session.begin():
                stmt = insert(DatasetLink).values(
                    token=token,
                    ipfs_link=ipfs_link,
                    timestamp=datetime.utcnow()
                ).on_conflict_do_update(
                    index_elements=['token'],  # Conflict resolution on token column
                    set_={
                        'ipfs_link': ipfs_link,
                        'timestamp': datetime.utcnow()
                    }
                )
                await session.execute(stmt)

    async def get_latest_link(self, token: str) -> str:
        """
        Retrieve the latest IPFS link for a specific token.

        Args:
            token (str): The token identifier.

        Returns:
            str: The latest IPFS link, or None if the token is not found.
        """
        async with self.session_manager.session() as session:
            query = select(DatasetLink.ipfs_link).where(DatasetLink.token == token)
            result = await session.execute(query)
            return result.scalar_one_or_none()
