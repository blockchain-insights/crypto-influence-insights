import streamlit as st
import pandas as pd
import requests
from src.subnet.dashboards.config import API_BASE_URL

def run():
    st.title("Influencer Detection Dashboard")
    st.write("Fetch and visualize top influencers for a specific token.")

    # Input fields for user input
    token = st.text_input("Token", value="TAO", help="Specify the token name.")
    min_follower_count = st.number_input("Min Follower Count", value=1000, help="Minimum number of followers.")
    limit = st.number_input("Limit", min_value=1, value=10, help="Maximum number of influencers to display.")
    time_period = st.number_input("Time Period (days)", value=30, help="Number of days to analyze.")

    if st.button("Fetch Influencers"):
        # Construct the API request URL
        url = (
            f"{API_BASE_URL}/{token}/detect-influencers?"
            f"min_follower_count={min_follower_count}&limit={limit}&"
            f"time_period={time_period}&response_type=json"
        )

        try:
            # Make the API request
            response = requests.get(url)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("results"):
                results = response_data["results"]
                st.success(f"Top {limit} influencers for token '{token}'")

                # Prepare data for visualization
                scatter_data = pd.DataFrame(
                    [{
                        "Username": r["user_name"],
                        "Follower Count": r["follower_count"],
                        "Engagement Level": r["engagement_level"],
                    } for r in results]
                )

                # Display results as a table
                st.write(
                    scatter_data.style
                    .set_properties(**{"text-align": "left"})
                    .background_gradient(subset=["Follower Count", "Engagement Level"], cmap="Blues")
                )

                # Scatter plot for visualization
                st.write("Follower Count vs. Engagement Level")
                st.vega_lite_chart(
                    scatter_data,
                    {
                        "mark": "circle",
                        "encoding": {
                            "x": {"field": "Follower Count", "type": "quantitative"},
                            "y": {"field": "Engagement Level", "type": "quantitative"},
                            "tooltip": [{"field": "Username", "type": "nominal"}]
                        }
                    },
                    use_container_width=True
                )
            else:
                # Handle cases where no results are found
                st.warning("No influencers found for the given parameters.")
        except Exception as e:
            # Handle errors during the request or processing
            st.error(f"Failed to fetch influencers: {e}")

# Main execution
if __name__ == "__main__":
    run()