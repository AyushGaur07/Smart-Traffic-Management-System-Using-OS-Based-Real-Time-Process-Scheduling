"""Smart Traffic Simulator — OS Scheduling and DBMS Integration.

Main application entry point launching the multi-page Streamlit web interface.
"""

import streamlit as st

# Configure page layout and title
st.set_page_config(
    page_title="Smart Traffic Simulator",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import frontend page renderers
from frontend.dashboard import render_dashboard
from frontend.simulator_page import render_simulator_page
from frontend.inputs_page import render_inputs_page
from frontend.scheduler_page import render_scheduler_page
from frontend.dbms_page import render_dbms_page
from frontend.architecture_page import render_architecture_page
from frontend.results_page import render_results_page
from frontend.settings_page import render_settings_page

from database.db_manager import DatabaseManager
from simulation.sumo_manager import SumoManager

def main():
    # Sidebar Header
    st.sidebar.title("🚦 Smart Traffic Sim")
    st.sidebar.caption("OS Scheduling & DBMS Integration")

    # Quick System Status in Sidebar
    db = DatabaseManager()
    sim_mgr = SumoManager()

    db_stat = db.test_connection()
    sumo_ok = sim_mgr.is_available()

    st.sidebar.markdown("### 🔌 System Status")
    if sumo_ok:
        st.sidebar.success("🟢 SUMO: Available")
    else:
        st.sidebar.error("🔴 SUMO: Missing")

    if db_stat.get("success") and db_stat.get("database_exists"):
        st.sidebar.success(f"🟢 MySQL: `{db.database}`")
    elif db_stat.get("success"):
        st.sidebar.warning("🟡 MySQL: No Database")
    else:
        st.sidebar.error("🔴 MySQL: Disconnected")

    st.sidebar.divider()

    # Page Navigation
    page = st.sidebar.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "🚗 Traffic Simulator",
            "📋 Inputs & Generation",
            "🖥️ OS CPU Scheduler",
            "🗄️ DBMS Explorer",
            "🏛️ Data Flow & Architecture",
            "🧪 Experiments & Results",
            "⚙️ Settings & Status"
        ],
        index=0
    )

    st.sidebar.divider()
    st.sidebar.caption("Academic Project — Python, TraCI, SUMO, MySQL 8.0")

    # Page Routing
    if page == "🏠 Dashboard":
        render_dashboard()
    elif page == "🚗 Traffic Simulator":
        render_simulator_page()
    elif page == "📋 Inputs & Generation":
        render_inputs_page()
    elif page == "🖥️ OS CPU Scheduler":
        render_scheduler_page()
    elif page == "🗄️ DBMS Explorer":
        render_dbms_page()
    elif page == "🏛️ Data Flow & Architecture":
        render_architecture_page()
    elif page == "🧪 Experiments & Results":
        render_results_page()
    elif page == "⚙️ Settings & Status":
        render_settings_page()

if __name__ == "__main__":
    main()
