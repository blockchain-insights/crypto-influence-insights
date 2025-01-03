from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os


def load_environment(env: str = "mainnet"):
    """Load the appropriate .env file based on the environment."""
    if env == 'mainnet':
        dotenv_path = os.path.abspath('../../../../env/.env.miner.mainnet')
    elif env == 'testnet':
        dotenv_path = os.path.abspath('../../../../env/.env.miner.testnet')
    else:
        raise ValueError(f"Unknown environment: {env}")

    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
    else:
        raise FileNotFoundError(f"Environment file not found: {dotenv_path}")


# Load the default environment
load_environment()


class MinerMigrationSettings(BaseSettings):
    DATABASE_URL: str
    model_config = SettingsConfigDict(extra='allow')
