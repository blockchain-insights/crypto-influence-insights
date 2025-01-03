import json
import requests
import argparse
from uuid import uuid4
import os

def download_dataset(ipfs_url):
    response = requests.get(ipfs_url)
    if response.status_code != 200:
        raise ValueError(f"Failed to download dataset from {ipfs_url}. HTTP status code: {response.status_code}")
    return response.json()

def replace_tweet_ids(dataset):
    for entry in dataset:
        if "tweet" in entry and "id" in entry["tweet"]:
            entry["tweet"]["id"] = str(uuid4())
    return dataset

def save_dataset(dataset, output_file):
    with open(output_file, "w") as f:
        json.dump(dataset, f, indent=4)
    print(f"Modified dataset saved to {output_file}")

def upload_to_pinata(file_path, pinata_api_key, pinata_secret_api_key):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": pinata_api_key,
        "pinata_secret_api_key": pinata_secret_api_key
    }
    files = {
        "file": (os.path.basename(file_path), open(file_path, "rb"))
    }
    response = requests.post(url, headers=headers, files=files)
    if response.status_code != 200:
        raise ValueError(f"Failed to upload file to Pinata. HTTP status code: {response.status_code}, Response: {response.text}")
    return response.json()

def main():
    parser = argparse.ArgumentParser(description="Replace tweet IDs in a dataset and re-upload to Pinata.")
    parser.add_argument("--ipfs", required=True, help="The IPFS URL of the dataset to download.")
    parser.add_argument("--output", default="modified_dataset.json", help="Output file for the modified dataset.")
    parser.add_argument("--pinata_api_key", required=True, help="Your Pinata API key.")
    parser.add_argument("--pinata_secret_api_key", required=True, help="Your Pinata Secret API key.")
    args = parser.parse_args()

    try:
        # Step 1: Download the dataset
        print("Downloading dataset...")
        dataset = download_dataset(args.ipfs)

        # Step 2: Replace tweet IDs
        print("Replacing tweet IDs...")
        modified_dataset = replace_tweet_ids(dataset)

        # Step 3: Save the modified dataset locally
        save_dataset(modified_dataset, args.output)

        # Step 4: Upload the modified dataset to Pinata
        print("Uploading modified dataset to Pinata...")
        upload_response = upload_to_pinata(args.output, args.pinata_api_key, args.pinata_secret_api_key)
        print("Upload successful. Pinata response:")
        print(json.dumps(upload_response, indent=4))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()