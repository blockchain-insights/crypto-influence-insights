import requests

def fetch_data(endpoint: str):
    """
    Fetch data from an API endpoint and return as JSON.
    """
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
