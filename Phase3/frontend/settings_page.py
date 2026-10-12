"""Settings and Connection Status Page.

Provides diagnostics for SUMO binaries, MySQL connection testing,
environment configuration inspection (with masked passwords), and log inspection.
"""

import sys
import platform
import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from config.settings import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER,
    get_sumo_binary, check_sumo_available, SUMO_FILES_DIR
)

def render_settings_page():
    st.title("⚙️ Settings and Connection Status")
    st.markdown("Inspect host environment configurations, verify binary dependencies, and audit system diagnostics.")

    db = DatabaseManager()

    # 1. System Diagnostics
    st.subheader("🖥️ Host System & Runtime Diagnostics")
    sys_diag = [
        {"Component": "Operating System", "Status": f"✅ {platform.system()} ({platform.release()})", "Detail": platform.version()},
        {"Component": "Python Version", "Status": f"✅ Python {platform.python_version()}", "Detail": sys.executable},
        {"Component": "SUMO Availability", "Status": "✅ Detected" if check_sumo_available() else "❌ Missing", "Detail": get_sumo_binary(False)},
        {"Component": "SUMO GUI", "Status": "✅ Available", "Detail": get_sumo_binary(True)},
        {"Component": "SUMO Scenario Directory", "Status": "✅ Present" if SUMO_FILES_DIR.exists() else "❌ Missing", "Detail": str(SUMO_FILES_DIR)},
    ]
    st.dataframe(pd.DataFrame(sys_diag), use_container_width=True)

    st.divider()

    # 2. Database Diagnostics
    st.subheader("🗄️ MySQL Connection Parameters & Live Test")
    
    col_host, col_port, col_db, col_user, col_pass = st.columns(5)
    col_host.text_input("DB Host", value=DB_HOST, disabled=True)
    col_port.text_input("DB Port", value=str(DB_PORT), disabled=True)
    col_db.text_input("DB Name", value=DB_NAME, disabled=True)
    col_user.text_input("DB User", value=DB_USER, disabled=True)
    col_pass.text_input("DB Password", value="••••••••", disabled=True)

    test_col1, test_col2 = st.columns(2)
    with test_col1:
        if st.button("🔌 Run Live MySQL Connection Test", use_container_width=True, type="primary"):
            test_res = db.test_connection()
            if test_res.get("success"):
                st.success(test_res["message"])
            else:
                st.error(test_res["message"])

    with test_col2:
        if st.button("🛠️ Verify / Re-initialize Database Schema", use_container_width=True):
            init_res = db.init_database_and_schema()
            if init_res.get("success"):
                st.success(init_res["message"])
            else:
                st.error(init_res["message"])

    st.divider()

    # 3. Environment Troubleshooting Guide
    st.subheader("💡 Troubleshooting & Setup Instructions")
    with st.expander("❓ How to troubleshoot MySQL connection errors", expanded=False):
        st.markdown(
            "1. **Check Service Status**: In Windows PowerShell, run `Get-Service -Name MySQL80`.\n"
            "   If stopped, run `Start-Service -Name MySQL80` as Administrator.\n"
            "2. **Verify Credentials**: Check your `.env` file in the project root:\n"
            "   ```ini\n"
            "   DB_HOST=localhost\n"
            "   DB_PORT=3306\n"
            "   DB_NAME=smart_traffic_db\n"
            "   DB_USER=root\n"
            "   DB_PASSWORD=your_password\n"
            "   ```\n"
            "3. **Ensure Database Exists**: Click the 'Verify / Re-initialize Database Schema' button above, "
            "which runs `CREATE DATABASE IF NOT EXISTS smart_traffic_db;` and executes `schema.sql`."
        )

    with st.expander("❓ How to troubleshoot SUMO & TraCI errors", expanded=False):
        st.markdown(
            "1. **Python SUMO Package**: This project utilizes `eclipse-sumo` installed via pip.\n"
            "   To verify or re-install: `pip install eclipse-sumo traci sumolib`\n"
            "2. **SUMO_HOME Environment Variable**: If using an independent SUMO installer, set `SUMO_HOME`:\n"
            "   `$env:SUMO_HOME = 'C:\\Program Files (x86)\\Eclipse\\Sumo'`\n"
            "3. **GUI Windows on Remote/Headless**: In headless environments, keep 'Open SUMO GUI Window' unchecked."
        )
