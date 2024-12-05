import os
import requests
import io
from fastapi import HTTPException
from dotenv import load_dotenv
from src.subnet.miner._config import MinerSettings, load_environment

# Load environment variables from .env
load_dotenv()
def upload_file_to_pinata(file_content: str, file_name: str, miner_key: str, settings: MinerSettings) -> dict:
    """
    Uploads a single file to Pinata's IPFS service under a directory-like naming convention.

    Args:
        file_content (str): Content of the file to be uploaded.
        file_name (str): Name of the file.
        miner_key (str): Logical directory name for the miner.
        settings (MinerSettings): Application settings containing Pinata API credentials.

    Returns:
        dict: Response from Pinata containing the file's CID and metadata.
    """
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": settings.PINATA_API_KEY,
        "pinata_secret_api_key": settings.PINATA_SECRET_API_KEY,
    }

    # Use in-memory file object
    file_like = io.BytesIO(file_content.encode("utf-8"))

    # Use miner_key as a logical folder prefix
    logical_path = os.path.join(miner_key, file_name)
    files = {"file": (logical_path, file_like)}

    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Pinata upload failed: {str(e)}"}

def get_ipfs_link(ipfs_hash: str) -> str:
    """
    Generate a public IPFS link for the given hash.

    Args:
        ipfs_hash (str): IPFS hash of the uploaded file.

    Returns:
        str: Public IPFS link.
    """
    return f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"