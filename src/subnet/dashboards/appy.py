import streamlit as st
from src.subnet.dashboards import (
    dashboard_influencers,
    dashboard_engagement_trends,
    dashboard_anomalies,
    dashboard_scam_alerts,
    dashboard_activity_snapshot,
)

# Get query parameters
query_params = st.experimental_get_query_params()
dashboard_name = query_params.get("dashboard", ["Influencers"])[0]

dashboards = {
    "Influencers": dashboard_influencers,
    "Engagement Trends": dashboard_engagement_trends,
    "Anomalies": dashboard_anomalies,
    "Scam Alerts": dashboard_scam_alerts,
    "Activity Snapshot": dashboard_activity_snapshot,
}

if dashboard_name in dashboards:
    dashboards[dashboard_name].run()
else:
    st.error(f"Dashboard '{dashboard_name}' not found.")
