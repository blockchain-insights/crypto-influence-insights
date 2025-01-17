import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from src.subnet.dashboards.config import API_BASE_URL

def run():
    st.title("Anomaly Detection Dashboard")
    st.write("Visualize anomalies in user activity for a specific token.")

    token = st.text_input("Token", value="TAO", help="Specify the token name.")

    if st.button("Detect Anomalies"):
        url = f"{API_BASE_URL}/{token}/detect-anomalies?response_type=json"

        try:
            response = requests.post(url)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("results"):
                results = response_data["results"]
                df = pd.DataFrame(results)

                st.write("Detected Anomalies:")

                # Display dataframe with adaptations
                st.dataframe(
                    df.style.set_properties(**{'text-align': 'left'}),
                    height=400,
                    use_container_width=True,
                )

                # Anomaly Distribution Chart
                st.write("Anomaly Distribution")
                anomaly_counts = df['anomaly_label'].explode().value_counts()

                # Create a bar chart with Matplotlib
                fig, ax = plt.subplots(figsize=(8, 4))  # Adjust figure size as needed
                anomaly_counts.plot(kind='bar', ax=ax, color='#ADD8E6', edgecolor='black')  # Light blue bars

                # Grayscale customization
                ax.set_facecolor("#f7f7f7")  # Light gray background for the plot
                ax.spines['top'].set_visible(False)  # Remove the top spine
                ax.spines['right'].set_visible(False)  # Remove the right spine
                ax.spines['left'].set_color("gray")  # Light gray for the left spine
                ax.spines['bottom'].set_color("gray")  # Light gray for the bottom spine
                ax.tick_params(axis='x', colors='gray', labelsize=10)  # X-axis ticks
                ax.tick_params(axis='y', colors='gray', labelsize=10)  # Y-axis ticks
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))  # Ensure y-axis ticks are integers

                # Customize labels
                ax.set_xlabel("Anomaly Types", fontsize=12, color='gray')
                ax.set_ylabel("Count", fontsize=12, color='gray')
                ax.set_title("Anomaly Distribution", fontsize=14, color='gray')
                ax.grid(axis='y', linestyle='--', alpha=0.5, color='gray')  # Light gray gridlines

                # Display the chart in Streamlit
                st.pyplot(fig)

            else:
                st.warning("No anomalies detected.")
        except Exception as e:
            st.error(f"Failed to detect anomalies: {e}")

# Main execution
if __name__ == "__main__":
    run()
