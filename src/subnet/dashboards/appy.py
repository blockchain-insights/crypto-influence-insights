import streamlit as st
from src.subnet.dashboards import (
    dashboard_influencers,
    dashboard_engagement_trends,
    dashboard_anomalies,
    dashboard_scam_alerts,
    dashboard_activity_snapshot,
)

# Mapping dashboard names to their respective modules
dashboards = {
    "Influencers": dashboard_influencers,
    "Engagement Trends": dashboard_engagement_trends,
    "Anomalies": dashboard_anomalies,
    "Scam Alerts": dashboard_scam_alerts,
    "Activity Snapshot": dashboard_activity_snapshot,
}

# Get query parameters
query_params = st.query_params
dashboard_name = query_params.get("dashboard")

# Main logic
if dashboard_name:
    # Extract the first query parameter value (full name)
    dashboard_name = dashboard_name.strip()

    # Check if the dashboard name exists in the dashboards dictionary
    if dashboard_name in dashboards:
        dashboards[dashboard_name].run()
    else:
        st.error(f"Dashboard '{dashboard_name}' not found.")
        st.markdown("[Go back to main page](http://localhost:8501)")
else:
    # Main page with links to dashboards
    st.title("Welcome to the Crypto Influence Insights App")
    st.write("Select a dashboard to explore insights:")

    # Dynamically generate links for dashboards
    for display_name, _ in dashboards.items():
        dashboard_url = f"?dashboard={display_name.replace(' ', '%20')}"
        st.markdown(f"- [{display_name}]({dashboard_url})")


