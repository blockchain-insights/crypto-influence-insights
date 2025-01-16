import streamlit as st
import requests
from src.subnet.dashboards.config import API_BASE_URL

def run():
    st.title("Engagement Trends Dashboard")
    st.write("Analyze daily or weekly engagement trends for a specific token.")

    token = st.text_input("Token", value="TAO", help="Specify the token name (e.g., 'TAO').")
    days = st.number_input("Days", min_value=1, max_value=365, value=30, help="Number of days to analyze.")
    region = st.text_input("Region", value="", help="Optional: Filter trends by region.")

    if st.button("Fetch Trends"):
        url = f"{API_BASE_URL}/{token}/get-engagement-trends?days={days}&region={region}&response_type=json"
        try:
            response = requests.get(url)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("results"):
                data = response_data["results"]

                # Extract and display data
                dates = [entry["date"] for entry in data]
                active_users = [entry["active_users"] for entry in data]
                engagement = [entry["daily_engagement"] for entry in data]

                # Plot charts
                st.line_chart({"Active Users": active_users, "Engagement": engagement}, use_container_width=True)
            else:
                st.warning("No trends found for the given parameters.")
        except Exception as e:
            st.error(f"Failed to fetch engagement trends: {e}")
