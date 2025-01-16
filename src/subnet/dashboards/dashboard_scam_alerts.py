import streamlit as st
import requests
from src.subnet.dashboards.config import API_BASE_URL

def run():
    st.title("Real-Time Scam Alerts Dashboard")
    st.write("Visualize recent scam alerts for a specific token.")

    token = st.text_input("Token", value="TAO", help="Specify the token name.")
    timeframe = st.text_input("Timeframe", value="24h", help="Specify the timeframe (e.g., '24h').")
    limit = st.number_input("Limit", min_value=1, max_value=100, value=10)

    if st.button("Fetch Scam Alerts"):
        url = f"{API_BASE_URL}/{token}/real-time-scam-alerts?timeframe={timeframe}&limit={limit}&response_type=json"

        try:
            response = requests.get(url)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("results"):
                results = response_data["results"]

                st.write("Recent Scam Alerts:")
                st.table(results)
            else:
                st.warning("No scam alerts found.")
        except Exception as e:
            st.error(f"Failed to fetch scam alerts: {e}")
