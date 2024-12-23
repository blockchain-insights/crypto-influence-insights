import io
import requests

def upload_file_to_ipfs(file_name: str, content: str, api_key: str, secret_api_key: str) -> dict:
    """
    Upload a file to IPFS using Pinata.

    Args:
        file_name (str): Name of the file to upload.
        content (str): File content to upload.
        api_key (str): Pinata API key.
        secret_api_key (str): Pinata secret API key.

    Returns:
        dict: Response from Pinata, including the file's CID and IPFS link.
    """
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": secret_api_key,
    }
    files = {"file": (file_name, io.BytesIO(content.encode("utf-8")))}

    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        result = response.json()
        ipfs_hash = result.get("IpfsHash")
        return {"file_name": file_name, "ipfs_hash": ipfs_hash, "ipfs_link": f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"}
    except requests.exceptions.RequestException as e:
        error_detail = e.response.text if e.response else str(e)
        return {"error": f"Failed to upload file to IPFS: {error_detail}"}

def fetch_file_from_ipfs(ipfs_hash: str) -> str:
    """
    Fetch a file from IPFS using its hash.

    Args:
        ipfs_hash (str): The IPFS hash of the file to fetch.

    Returns:
        str: Content of the fetched file.
    """
    url = f"https://gateway.pinata.cloud/ipfs/{ipfs_hash}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        error_detail = e.response.text if e.response else str(e)
        raise RuntimeError(f"Failed to fetch file from IPFS: {error_detail}")
