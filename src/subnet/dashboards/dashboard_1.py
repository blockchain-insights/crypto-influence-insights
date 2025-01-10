import streamlit as st
import requests
from src.subnet.dashboards.config import API_BASE_URL  # Ensure this config contains the correct API base URL

def run():
    # Title and description
    st.title("Influencer Detection Dashboard")
    st.write("This dashboard fetches top influencers for a specific token based on their engagement and followers.")

    # Input fields with unique keys
    token = st.text_input(
        "Token", value="TAO", help="Specify the token name (e.g., 'TAO').", key="token_input"
    )
    min_follower_count = st.number_input(
        "Minimum Follower Count", min_value=0, value=1000, help="Minimum number of followers to filter influencers.", key="min_follower_input"
    )
    limit = st.number_input(
        "Limit", min_value=1, max_value=100, value=10, help="Maximum number of influencers to fetch.", key="limit_input"
    )
    time_period = st.number_input(
        "Time Period (days)", min_value=1, value=30, help="Number of days to look back for influencer activity.", key="time_period_input"
    )
    min_tweet_count = st.number_input(
        "Minimum Tweet Count", min_value=0, value=0, help="Minimum number of tweets required to qualify.", key="min_tweet_input"
    )

    # Fetch button
    if st.button("Fetch Influencers", key="fetch_button"):
        # Build the API URL
        url = (
            f"{API_BASE_URL}/{token}/detect-influencers?"
            f"min_follower_count={min_follower_count}&limit={limit}"
            f"&time_period={time_period}&min_tweet_count={min_tweet_count}&response_type=json"
        )

        try:
            # Make the API request
            response = requests.get(url)
            response_data = response.json()

            if response.status_code == 200:
                # Extract results and display in a table
                results = response_data.get("results", [])
                if results:
                    st.success(f"Top {limit} influencers for token '{token}':")
                    # Format the results as a table
                    st.table(
                        [
                            {
                                "User ID": r.get("user_id"),
                                "Username": r.get("user_name"),
                                "Follower Count": r.get("follower_count"),
                                "Verified": r.get("verified"),
                                "Engagement Level": r.get("engagement_level"),
                                "Total Tweets": r.get("total_tweets"),
                                "Combined Score": r.get("combined_score"),
                            }
                            for r in results
                        ]
                    )
                else:
                    st.warning("No influencers found for the given parameters.")
            else:
                # Handle API error
                st.error(f"Error {response.status_code}: {response_data.get('message', 'Unknown error')}")
        except Exception as e:
            # Handle request failure
            st.error(f"Failed to fetch data: {e}")


# Main execution
if __name__ == "__main__":
    run()
