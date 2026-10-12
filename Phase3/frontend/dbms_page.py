"""DBMS Explorer Page.

Directly inspects the live MySQL database, showing real tables, column types,
foreign key relationships, stored row counts, paginated data records, and
the exact SQL queries executed by the application.
"""

import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from database.repositories import TABLE_DOCUMENTATION

def render_dbms_page():
    st.title("🗄️ MySQL DBMS Explorer")
    st.markdown(
        "Live inspection of the **MySQL Server** database. Examine table structures, "
        "foreign key constraints, stored records, and SQL queries in real time."
    )

    db = DatabaseManager()

    # 1. Connection Diagnostic Header
    st.subheader("🔌 Connection Status & Diagnostics")
    conn_info = db.test_connection()

    col_stat, col_btn1, col_btn2 = st.columns([2, 1, 1])

    with col_stat:
        if conn_info.get("success") and conn_info.get("database_exists"):
            st.success(f"🟢 **Connected:** MySQL Server {conn_info.get('server_version')} | Database: `{conn_info.get('database_name')}`")
        elif conn_info.get("success"):
            st.warning(f"🟡 **Connected to Server**, but database `{conn_info.get('database_name')}` is not created yet.")
        else:
            st.error(f"🔴 **Connection Failed:** {conn_info.get('message')}")
            st.info("Check your `.env` configuration file or ensure the MySQL80 service is running.")
            return

    with col_btn1:
        if st.button("🔄 Test Connection", use_container_width=True):
            st.rerun()

    with col_btn2:
        if st.button("🛠️ Initialize Schema", use_container_width=True, help="Executes schema.sql statements safely."):
            init_res = db.init_database_and_schema()
            if init_res.get("success"):
                st.success(init_res["message"])
                st.rerun()
            else:
                st.error(init_res["message"])

    st.divider()

    # 2. Table Summary & Row Counts
    st.subheader("📊 Database Tables & Live Row Counts")
    tables = db.get_tables()
    row_counts = db.get_row_counts()

    if not tables:
        st.warning("No tables found in database. Click 'Initialize Schema' above to generate tables from schema.sql.")
        return

    table_summary = [
        {
            "Table Name": t,
            "Total Rows": row_counts.get(t, 0),
            "Category": (
                "Traffic Telemetry" if "sim" in t or "snapshot" in t or "vehicle" in t or "signal" in t
                else "CPU Scheduling" if "sched" in t
                else "Benchmarking"
            )
        }
        for t in tables
    ]
    st.dataframe(pd.DataFrame(table_summary), use_container_width=True)

    st.divider()

    # 3. Detailed Table Inspector
    st.subheader("🔍 Inspect Specific Table")
    selected_table = st.selectbox("Select Table to Explore", tables, index=0)

    # Documentation Card
    doc = TABLE_DOCUMENTATION.get(selected_table, {})
    with st.expander(f"📖 Academic Documentation for `{selected_table}`", expanded=True):
        st.markdown(f"**Description:** {doc.get('description', 'N/A')}")
        dcol1, dcol2 = st.columns(2)
        dcol1.markdown(f"**Written by:** `{doc.get('written_by', 'N/A')}`")
        dcol1.markdown(f"**Read by:** `{doc.get('read_by', 'N/A')}`")
        dcol2.markdown(f"**Insertion Trigger:** {doc.get('insertion_trigger', 'N/A')}")
        dcol2.markdown(f"**Relationships:** {doc.get('relations', 'N/A')}")

    # Tabs for Schema vs Data vs SQL
    tab_data, tab_schema, tab_keys, tab_sql = st.tabs([
        "📄 Stored Rows", "📐 Schema Structure", "🔗 Foreign Keys", "💻 SQL Statements"
    ])

    with tab_data:
        st.caption(f"Showing live rows from table `{selected_table}` (Row Count: {row_counts.get(selected_table, 0)}).")
        limit = st.slider("Record Limit", min_value=10, max_value=200, value=50, step=10, key=f"lim_{selected_table}")
        
        try:
            rows = db.get_table_rows(selected_table, limit=limit)
            if rows:
                df_rows = pd.DataFrame(rows)
                st.dataframe(df_rows, use_container_width=True)
            else:
                st.info(f"Table `{selected_table}` is currently empty. Run a simulation or scheduler demo to generate rows.")
        except Exception as e:
            st.error(f"Error querying rows: {e}")

    with tab_schema:
        cols = db.get_table_columns(selected_table)
        if cols:
            df_cols = pd.DataFrame(cols)
            st.dataframe(df_cols, use_container_width=True)

    with tab_keys:
        fks = db.get_foreign_keys(selected_table)
        if fks:
            df_fks = pd.DataFrame(fks)
            st.dataframe(df_fks, use_container_width=True)
        else:
            st.info(f"Table `{selected_table}` has no outbound foreign key constraints (or is a root table).")

    with tab_sql:
        st.markdown(f"**Primary SQL Queries executed by the application for `{selected_table}`:**")
        if selected_table == "simulation_runs":
            st.code(
                "-- Insert new run record upon starting:\n"
                "INSERT INTO simulation_runs (junction_id, scenario_name, duration_seconds, step_length, status)\n"
                "VALUES (%s, %s, %s, %s, 'RUNNING');\n\n"
                "-- Update aggregate metrics upon completion:\n"
                "UPDATE simulation_runs\n"
                "SET status = 'COMPLETED', total_generated = %s, total_completed = %s,\n"
                "    avg_speed_kmh = %s, avg_waiting_time = %s, completed_at = CURRENT_TIMESTAMP\n"
                "WHERE run_id = %s;\n\n"
                "-- Query recent runs:\n"
                "SELECT * FROM simulation_runs ORDER BY run_id DESC LIMIT 50;",
                language="sql"
            )
        elif selected_table == "traffic_snapshots":
            st.code(
                "-- Batch insert high-frequency telemetry at each observation tick:\n"
                "INSERT INTO traffic_snapshots (\n"
                "    run_id, sim_time, phase_index, phase_name, active_corridor,\n"
                "    active_vehicles, completed_vehicles, north_queue, south_queue,\n"
                "    east_queue, west_queue, avg_speed_kmh, avg_waiting_time, throughput_per_min\n"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);\n\n"
                "-- Query chronological snapshots for a specific run:\n"
                "SELECT * FROM traffic_snapshots WHERE run_id = %s ORDER BY sim_time ASC;",
                language="sql"
            )
        elif selected_table == "scheduler_runs":
            st.code(
                "-- Record scheduler execution batch:\n"
                "INSERT INTO scheduler_runs (\n"
                "    algorithm, task_count, total_burst_time, avg_waiting_time,\n"
                "    avg_turnaround_time, context_switches, time_quantum, preemptive\n"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s);\n\n"
                "-- Retrieve recent scheduler runs:\n"
                "SELECT * FROM scheduler_runs ORDER BY scheduler_run_id DESC LIMIT 50;",
                language="sql"
            )
        else:
            st.code(
                f"-- Standard parameterized read for {selected_table}:\n"
                f"SELECT * FROM `{selected_table}` ORDER BY 1 DESC LIMIT 100;",
                language="sql"
            )
