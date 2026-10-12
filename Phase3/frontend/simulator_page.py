"""Traffic Simulator Page.

Provides interactive controls to run SUMO simulations (headless or GUI),
monitor approach queue dynamics and signal phase progression, and persist
telemetry snapshots directly to MySQL.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from simulation.sumo_manager import SumoManager, SimulationState
from services.simulation_service import SimulationService
from config.settings import TRAFFIC_SCENARIOS, DEFAULT_SIMULATION_DURATION

def render_simulator_page():
    st.title("🚗 SUMO Traffic Simulator")
    st.markdown(
        "Operate the **4-arm Junction J0** traffic simulation in real-time or batch mode. "
        "Observe vehicle queuing, traffic light phase actuation, and speed variations."
    )

    sim_service = SimulationService()
    sim_available = sim_service.manager.is_available()

    if not sim_available:
        st.error("⚠️ Eclipse SUMO is not detected on this system. Please check the Settings page.")
        return

    # Configuration sidebar / controls
    st.subheader("⚙️ Simulation Configuration")
    col1, col2, col3 = st.columns(3)

    with col1:
        scenario = st.selectbox(
            "Traffic Demand Scenario",
            list(TRAFFIC_SCENARIOS.keys()),
            index=1,
            help="Configures departure frequency and vehicle volume across all 4 approaches."
        )
        st.caption(TRAFFIC_SCENARIOS[scenario]["description"])

    with col2:
        duration = st.slider(
            "Simulation Duration (seconds)",
            min_value=15,
            max_value=180,
            value=60,
            step=15
        )

    with col3:
        use_gui = st.checkbox(
            "Open SUMO GUI Window",
            value=False,
            help="Launches sumo-gui.exe for visual vehicle rendering. Uncheck for fast headless simulation."
        )
        persist_db = st.checkbox(
            "Persist Run & Snapshots to MySQL",
            value=True,
            help="Automatically saves the simulation run, snapshots, and vehicle observations to MySQL."
        )

    # Additional GUI controls when GUI window is requested
    gui_delay = 150
    quit_gui = False
    if use_gui:
        gcol1, gcol2 = st.columns(2)
        with gcol1:
            gui_delay = st.slider(
                "GUI Animation Delay (ms per step)",
                min_value=50,
                max_value=400,
                value=150,
                step=25,
                help="Slows down simulation playback in the SUMO window so vehicles and queues can be observed smoothly."
            )
        with gcol2:
            quit_gui = st.checkbox(
                "Close GUI window automatically when finished",
                value=False,
                help="Leave unchecked to keep SUMO GUI open after the simulation finishes so you can zoom in and inspect vehicles."
            )

    st.divider()

    # Execution Action Bar
    btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 2])

    with btn_col1:
        start_batch = st.button("▶️ Execute Full Simulation Run", use_container_width=True, type="primary")

    with btn_col2:
        launch_gui = st.button("🖥️ Open Scenario in SUMO GUI (Free Explore)", use_container_width=True)

    with btn_col3:
        st.button("⏹️ Reset State", use_container_width=True, on_click=lambda: st.session_state.pop("sim_run_data", None))

    # Handle Launch Standalone GUI
    if launch_gui:
        sim_service.manager.launch_standalone_gui(delay_ms=gui_delay)
        st.success(
            "🖥️ **SUMO GUI Opened!** Look on your taskbar for the Eclipse SUMO window. "
            "Press the green **Play** button, adjust zoom, and inspect Junction J0 directly!"
        )

    # Handle Batch Run
    if start_batch:
        with st.spinner(f"Running SUMO ({scenario}, {duration}s)..."):
            if persist_db:
                res = sim_service.execute_and_persist(
                    scenario=scenario,
                    duration=duration,
                    use_gui=use_gui,
                    gui_delay_ms=gui_delay,
                    quit_on_end=quit_gui
                )
                st.session_state["sim_run_data"] = res
                st.success(f"Simulation completed and persisted as Run #{res['run_id']} in MySQL!")
            else:
                snapshots = sim_service.manager.run_complete(
                    scenario=scenario,
                    duration=duration,
                    use_gui=use_gui,
                    gui_delay_ms=gui_delay,
                    quit_on_end=quit_gui
                )
                summary = sim_service.manager.metrics_tracker.get_summary()
                st.session_state["sim_run_data"] = {
                    "run_id": "Unsaved",
                    "scenario": scenario,
                    "duration": duration,
                    "summary": summary,
                    "snapshots": snapshots
                }
                st.success("Simulation completed (in-memory mode).")

    # Render Simulation Results
    sim_data = st.session_state.get("sim_run_data")
    if sim_data:
        st.divider()
        st.subheader("📈 Simulation Metrics & Telemetry")

        summary = sim_data.get("summary", {})
        snapshots = sim_data.get("snapshots", [])

        # Metric KPIs
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Total Generated", summary.get("total_generated", 0))
        m_col2.metric("Trips Completed", summary.get("total_completed", 0))
        m_col3.metric("Avg Travel Time", f"{summary.get('avg_travel_time', 0.0)} s")
        m_col4.metric("Avg Waiting Delay", f"{summary.get('avg_waiting_time', 0.0)} s")

        if snapshots:
            df_snaps = pd.DataFrame(snapshots)

            # Approach Queue Chart
            st.subheader("🚗 Queue Dynamics by Inbound Approach (Vehicles Stopped < 0.1 m/s)")
            fig_queues = go.Figure()
            fig_queues.add_trace(go.Scatter(x=df_snaps["sim_time"], y=df_snaps["north_queue"], name="North Approach", line=dict(color="#1f77b4", width=2)))
            fig_queues.add_trace(go.Scatter(x=df_snaps["sim_time"], y=df_snaps["south_queue"], name="South Approach", line=dict(color="#aec7e8", width=2)))
            fig_queues.add_trace(go.Scatter(x=df_snaps["sim_time"], y=df_snaps["east_queue"], name="East Approach", line=dict(color="#ff7f0e", width=2)))
            fig_queues.add_trace(go.Scatter(x=df_snaps["sim_time"], y=df_snaps["west_queue"], name="West Approach", line=dict(color="#ffbb78", width=2)))
            fig_queues.update_layout(
                xaxis_title="Simulation Time (seconds)",
                yaxis_title="Vehicles in Queue",
                template="plotly_white",
                height=350,
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_queues, use_container_width=True)

            # Speed and Delay Chart
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("🏎️ Average Network Speed (km/h)")
                fig_speed = px.line(df_snaps, x="sim_time", y="avg_speed_kmh", template="plotly_white")
                fig_speed.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_speed, use_container_width=True)

            with col_chart2:
                st.subheader("⏱️ Average Vehicle Delay (seconds)")
                fig_delay = px.line(df_snaps, x="sim_time", y="avg_waiting_time", color_discrete_sequence=["#d62728"], template="plotly_white")
                fig_delay.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_delay, use_container_width=True)

            # Snapshots Data Table Inspector
            with st.expander("🔍 Inspect Raw TraCI Step Telemetry (First 50 Steps)"):
                st.dataframe(df_snaps.head(50), use_container_width=True)
    else:
        st.info("💡 Click **'Execute Full Simulation Run'** above to launch the simulation and visualize real traffic flow.")
