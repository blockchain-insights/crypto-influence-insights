import json
import io
import requests
from datetime import datetime

def get_ipfs_link(ipfs_hash: str) -> str:
    """
    Generate a public IPFS link for the given hash.

    Args:
        ipfs_hash (str): IPFS hash of the uploaded file.

    Returns:
        str: Public IPFS link.
    """
    return f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"


def upload_file_to_pinata(file_name: str, content: str, settings) -> dict:
    """
    Upload a single file to Pinata.

    Args:
        file_name (str): Name of the file.
        content (str): Content of the file.
        settings: Application settings containing Pinata API credentials.

    Returns:
        dict: Response from Pinata.
    """
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": settings.PINATA_API_KEY,
        "pinata_secret_api_key": settings.PINATA_SECRET_API_KEY,
    }

    files = {
        "file": (file_name, io.BytesIO(content.encode("utf-8"))),
    }

    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_detail = e.response.text if e.response else str(e)
        return {"error": f"Pinata upload failed: {error_detail}"}


def delete_old_snapshots(miner_key: str, settings) -> None:
    """
    Delete old snapshots prefixed with the given miner_key from Pinata.

    Args:
        miner_key (str): The prefix for identifying old snapshots.
        settings: Application settings containing Pinata API credentials.
    """
    url = "https://api.pinata.cloud/data/pinList"
    headers = {
        "pinata_api_key": settings.PINATA_API_KEY,
        "pinata_secret_api_key": settings.PINATA_SECRET_API_KEY,
    }

    try:
        # Fetch the list of pinned files
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        pinned_files = response.json().get("rows", [])

        # Filter files with the given miner_key prefix
        for file in pinned_files:
            file_name = file.get("metadata", {}).get("name", "")
            if file_name.startswith(f"{miner_key}_"):
                cid = file.get("ipfs_pin_hash")
                if cid:
                    # Unpin each matching file
                    unpin_url = f"https://api.pinata.cloud/pinning/unpin/{cid}"
                    unpin_response = requests.delete(unpin_url, headers=headers)
                    unpin_response.raise_for_status()
                    print(f"Unpinned old snapshot: {file_name} (CID: {cid})")
    except requests.exceptions.RequestException as e:
        print(f"Error deleting old snapshots for miner_key '{miner_key}': {e}")