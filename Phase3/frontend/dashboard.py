"""Dashboard Page.

Displays holistic system health, SUMO and MySQL connectivity, active junction status,
latest simulation and scheduler metrics, and quick execution actions.
"""

import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from database.repositories import SimulationRepository, SchedulerRepository
from simulation.sumo_manager import SumoManager
from services.simulation_service import SimulationService
from services.scheduler_service import SchedulerService

def render_dashboard():
    st.title("🚦 Smart Traffic Simulator Dashboard")
    st.markdown(
        "**OS Scheduling and DBMS Integration** — An educational platform integrating "
        "**Eclipse SUMO**, **Python TraCI**, **OS CPU Scheduling**, and **MySQL 8.0**."
    )

    db = DatabaseManager()
    sim_mgr = SumoManager()
    sim_repo = SimulationRepository(db)
    sched_repo = SchedulerRepository(db)

    # 1. System Health Row
    col1, col2, col3, col4 = st.columns(4)

    # Check SUMO
    sumo_ok = sim_mgr.is_available()
    with col1:
        if sumo_ok:
            st.success("🟢 SUMO Engine: Ready")
        else:
            st.error("🔴 SUMO Engine: Missing")

    # Check MySQL
    db_status = db.test_connection()
    with col2:
        if db_status.get("success") and db_status.get("database_exists"):
            st.success(f"🟢 MySQL: Connected ({db.database})")
        elif db_status.get("success"):
            st.warning("🟡 MySQL: Connected (No DB)")
        else:
            st.error("🔴 MySQL: Disconnected")

    # Recent Simulation Runs Count
    sim_runs = []
    try:
        sim_runs = sim_repo.get_simulation_runs(limit=1)
    except Exception:
        pass

    with col3:
        if sim_runs:
            st.metric("Latest Sim Run", f"Run #{sim_runs[0]['run_id']}", f"{sim_runs[0]['scenario_name']}")
        else:
            st.metric("Latest Sim Run", "None", "No runs yet")

    # Recent Scheduler Runs Count
    sched_runs = []
    try:
        sched_runs = sched_repo.get_scheduler_runs(limit=1)
    except Exception:
        pass

    with col4:
        if sched_runs:
            st.metric("Latest Scheduler Run", f"Run #{sched_runs[0]['scheduler_run_id']}", f"{sched_runs[0]['algorithm']}")
        else:
            st.metric("Latest Scheduler Run", "None", "No runs yet")

    st.divider()

    # 2. Quick Execution Action Bar
    st.subheader("⚡ Quick Actions")
    q_col1, q_col2, q_col3 = st.columns(3)

    with q_col1:
        if st.button("🚀 Run Quick Headless Sim (30s)", use_container_width=True):
            with st.spinner("Running SUMO simulation and persisting to MySQL..."):
                sim_service = SimulationService()
                res = sim_service.execute_and_persist(scenario="Low Demand", duration=30)
                st.session_state["latest_sim_result"] = res
                st.success(f"Simulation completed! Saved as Run #{res['run_id']} in MySQL.")
                st.rerun()

    with q_col2:
        if st.button("⏱️ Run Quick Scheduler Demo (FCFS)", use_container_width=True):
            with st.spinner("Executing user-space FCFS scheduler..."):
                sched_service = SchedulerService()
                tasks = sched_service.generate_traffic_event_tasks()
                res = sched_service.run_algorithm("FCFS", tasks, persist_to_db=True)
                st.session_state["latest_sched_result"] = res
                st.success(f"FCFS executed! Avg Wait: {res.avg_waiting_time} ticks. Persisted to MySQL.")
                st.rerun()

    with q_col3:
        if st.button("🔄 Refresh Database Status", use_container_width=True):
            st.rerun()

    st.divider()

    # 3. Latest Telemetry Overview
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 Recent Simulation Runs in MySQL")
        try:
            recent_sims = sim_repo.get_simulation_runs(limit=5)
            if recent_sims:
                df_sims = pd.DataFrame(recent_sims)
                cols_to_show = ["run_id", "scenario_name", "duration_seconds", "total_generated", "total_completed", "avg_waiting_time"]
                available_cols = [c for c in cols_to_show if c in df_sims.columns]
                st.dataframe(df_sims[available_cols], use_container_width=True)
            else:
                st.info("No simulation records in MySQL. Click 'Run Quick Headless Sim' above to generate records.")
        except Exception as e:
            st.error(f"Error querying simulation_runs: {e}")

    with col_right:
        st.subheader("⚙️ Recent Scheduler Runs in MySQL")
        try:
            recent_sched = sched_repo.get_scheduler_runs(limit=5)
            if recent_sched:
                df_sched = pd.DataFrame(recent_sched)
                cols_to_show = ["scheduler_run_id", "algorithm", "task_count", "avg_waiting_time", "avg_turnaround_time", "context_switches"]
                available_cols = [c for c in cols_to_show if c in df_sched.columns]
                st.dataframe(df_sched[available_cols], use_container_width=True)
            else:
                st.info("No scheduler records in MySQL. Click 'Run Quick Scheduler Demo' to generate records.")
        except Exception as e:
            st.error(f"Error querying scheduler_runs: {e}")

    # 4. System Architectural Overview
    st.divider()
    st.subheader("🧩 Integrated System Architecture")
    st.info(
        "**How components connect in real time:**\n\n"
        "1. **SUMO & TraCI**: Injects vehicles into the 4-arm junction `J0` and simulates physical car-following dynamics.\n"
        "2. **Simulation Manager**: Advances simulation steps, monitors queues, and collects vehicle metrics.\n"
        "3. **Python OS Scheduler**: Receives traffic management events as educational CPU tasks and calculates scheduling timelines.\n"
        "4. **MySQL Database**: Permanently stores runs, high-frequency snapshots, vehicle journeys, signal states, and task metrics.\n"
        "5. **Streamlit UI**: Interactively controls the simulation, inspects live DBMS tables, and displays performance metrics."
    )
