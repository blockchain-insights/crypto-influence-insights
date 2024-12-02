from typing import Optional
from loguru import logger
from src.subnet.validator.validator import Validator

class SnapshotService:
    def __init__(self, validator: Validator):
        """
        Initializes the SnapshotService with a validator instance.

        Args:
            validator (Validator): The validator instance for interacting with miners.
        """
        self.validator = validator

    async def get_snapshot(self, token: str, from_date: str, to_date: str, miner_key: Optional[str] = None) -> dict:
        """
        Fetches a snapshot from the validator by calling the fetch_snapshot function.

        Args:
            token (str): The token name to filter by.
            from_date (str): The start date for filtering (YYYY-MM-DD).
            to_date (str): The end date for filtering (YYYY-MM-DD).
            miner_key (Optional[str]): Specific miner key to query. If None, miners will be sampled.

        Returns:
            dict: Snapshot data including metadata and response content.
        """
        try:
            logger.info(f"Fetching snapshot for token '{token}' from {from_date} to {to_date}, miner_key: {miner_key}")
            response = await self.validator.fetch_snapshot(token, from_date, to_date, miner_key)
            logger.info(f"Snapshot fetched successfully: {response}")
            return response
        except Exception as e:
            logger.error(f"Error fetching snapshot: {str(e)}")
            raise Exception(f"Error fetching snapshot: {str(e)}")
