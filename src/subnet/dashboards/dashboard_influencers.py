import streamlit as st
import requests
from src.subnet.dashboards.config import API_BASE_URL

def run():
    st.title("Influencer Detection Dashboard")
    st.write("Fetch and visualize top influencers for a specific token.")

    token = st.text_input("Token", value="TAO", help="Specify the token name.")
    min_follower_count = st.number_input("Min Follower Count", value=1000)
    limit = st.number_input("Limit", min_value=1, value=10)
    time_period = st.number_input("Time Period (days)", value=30)

    if st.button("Fetch Influencers"):
        url = f"{API_BASE_URL}/{token}/detect-influencers?min_follower_count={min_follower_count}&limit={limit}&time_period={time_period}&response_type=json"

        try:
            response = requests.get(url)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("results"):
                results = response_data["results"]
                st.success(f"Top {limit} influencers for token '{token}'")

                # Extract data for visualization
                usernames = [r["user_name"] for r in results]
                follower_counts = [r["follower_count"] for r in results]
                engagement_levels = [r["engagement_level"] for r in results]

                # Display as a table
                st.table(results)

                # Scatter plot
                st.write("Follower Count vs. Engagement Level")
                st.scatter_chart({"Follower Count": follower_counts, "Engagement Level": engagement_levels})
            else:
                st.warning("No influencers found.")
        except Exception as e:
            st.error(f"Failed to fetch influencers: {e}")
