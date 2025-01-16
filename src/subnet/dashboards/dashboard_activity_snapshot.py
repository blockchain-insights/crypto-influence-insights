import streamlit as st
import requests
from src.subnet.dashboards.config import API_BASE_URL

def run():
    st.title("Token Activity Snapshot")
    st.write("Analyze aggregated activity for a specific token.")

    token = st.text_input("Token", value="TAO", help="Specify the token name.")
    timeframe = st.text_input("Timeframe", value="7d", help="Specify the timeframe (e.g., '7d').")

    if st.button("Fetch Activity Snapshot"):
        url = f"{API_BASE_URL}/{token}/activity-snapshot?timeframe={timeframe}&response_type=json"

        try:
            response = requests.get(url)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("results"):
                data = response_data["results"]

                st.write("Activity Snapshot:")
                st.table(data)
                # Example visualization: Mentions over time
                st.line_chart({entry["date"]: entry["total_mentions"] for entry in data})
            else:
                st.warning("No activity snapshot found.")
        except Exception as e:
            st.error(f"Failed to fetch activity snapshot: {e}")
