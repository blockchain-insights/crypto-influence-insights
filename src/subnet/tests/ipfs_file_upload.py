import json
import io
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

class PinataSettings:
    """
    Configuration for Pinata API.
    Replace the values below with your actual Pinata API credentials.
    """
    PINATA_API_KEY = "c0be7f0fb0ab8e2078d2"
    PINATA_SECRET_API_KEY = "867de77b4bd6766fad1e23cc1b2ab7effc864856d9b2ae8058b29f44f87c8bae"


def upload_directory_to_pinata(file_dict: dict, folder_name: str, settings) -> dict:
    """
    Upload multiple files to Pinata, simulating folder behavior via metadata.

    Args:
        file_dict (dict): A dictionary of filenames and their content.
        folder_name (str): Name of the logical folder.
        settings: Application settings containing Pinata API credentials.

    Returns:
        dict: Response summarizing the uploads, including successes and failures.
    """
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": settings.PINATA_API_KEY,
        "pinata_secret_api_key": settings.PINATA_SECRET_API_KEY,
    }

    # Initialize result dictionary
    result_summary = {
        "success": [],
        "failure": [],
        "new_folder_cid": None
    }

    for file_name, content in file_dict.items():
        # Create metadata for the file
        metadata = {
            "name": file_name,
            "keyvalues": {"folder": folder_name}
        }

        # Serialize metadata to JSON
        metadata_json = json.dumps(metadata)

        # Create multipart form data
        files = {
            "file": (file_name, io.BytesIO(content.encode("utf-8"))),
            "pinataMetadata": (None, metadata_json, "application/json"),
        }

        try:
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()

            # Append success result
            result_summary["success"].append({
                "file_name": file_name,
                "response": response.json()
            })
        except requests.exceptions.RequestException as e:
            error_detail = e.response.text if e.response else str(e)
            result_summary["failure"].append({
                "file_name": file_name,
                "error": f"Pinata upload failed: {error_detail}"
            })

    # Generate a new pseudo-folder CID for grouping
    result_summary["new_folder_cid"] = _generate_virtual_folder_cid(result_summary["success"])
    return result_summary


def _generate_virtual_folder_cid(files: list) -> str:
    """
    Generate a simulated CID for a folder based on its files.

    Args:
        files (list): A list of uploaded file metadata.

    Returns:
        str: A pseudo-CID representing the folder.
    """
    from hashlib import sha256
    combined_cids = "".join(file["response"].get("IpfsHash", "") for file in files)
    return sha256(combined_cids.encode("utf-8")).hexdigest()


def test_upload_files_to_ipfs_folder():
    """
    Test uploading two files (a.txt and b.txt) with arbitrary text to a folder named 'test_text'.
    """
    # Define the folder name and file contents
    folder_name = "test_text"
    file_dict = {
        "a.txt": "This is the content of file A.",
        "b.txt": "This is the content of file B."
    }

    # Attempt to upload the files
    try:
        settings = PinataSettings()
        response = upload_directory_to_pinata(file_dict, folder_name, settings)
        print("Upload Response:")
        print(json.dumps(response, indent=4))
    except Exception as e:
        print(f"Error during test upload: {str(e)}")


if __name__ == "__main__":
    test_upload_files_to_ipfs_folder()
