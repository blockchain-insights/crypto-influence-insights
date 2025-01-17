import streamlit as st
import requests
import matplotlib.pyplot as plt
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

                # Extract data for the chart
                dates = [entry["date"] for entry in data]
                mentions = [entry["total_mentions"] for entry in data]

                # Create the plot
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(dates, mentions, color="lightblue", linewidth=2)

                # Set chart title and labels
                ax.set_title("Token Activity Snapshot", fontsize=14, color="gray")
                ax.set_xlabel("Date", fontsize=12, color="gray")
                ax.set_ylabel("Total Mentions", fontsize=12, color="gray")

                # Customize tick colors and gridlines
                ax.tick_params(colors="gray", labelsize=10)
                ax.grid(color="lightgray", linestyle="--", linewidth=0.5)

                # Apply a clean layout
                fig.tight_layout()

                # Display the chart in Streamlit
                st.pyplot(fig)

            else:
                st.warning("No activity snapshot found.")
        except Exception as e:
            st.error(f"Failed to fetch activity snapshot: {e}")

# Main execution
if __name__ == "__main__":
    run()
