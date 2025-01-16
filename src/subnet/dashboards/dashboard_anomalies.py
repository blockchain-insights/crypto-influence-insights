import streamlit as st
import requests
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

                st.write("Detected Anomalies:")
                st.table(results)

                # Pie chart for anomaly distribution
                anomaly_types = [anomaly["anomaly_label"] for anomaly in results]
                st.write("Anomaly Distribution")
                st.bar_chart(anomaly_types)
            else:
                st.warning("No anomalies detected.")
        except Exception as e:
            st.error(f"Failed to detect anomalies: {e}")
