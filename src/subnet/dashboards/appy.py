import streamlit as st
from src.subnet.dashboards import dashboard_1, dashboard_2, dashboard_3

# Get query parameters
query_params = st.experimental_get_query_params()
dashboard_name = query_params.get("dashboard", ["Dashboard 1"])[0]

dashboards = {
    "Dashboard 1": dashboard_1,
    "Dashboard 2": dashboard_2,
    "Dashboard 3": dashboard_3,
}

if dashboard_name in dashboards:
    dashboards[dashboard_name].run()
else:
    st.error(f"Dashboard '{dashboard_name}' not found.")
