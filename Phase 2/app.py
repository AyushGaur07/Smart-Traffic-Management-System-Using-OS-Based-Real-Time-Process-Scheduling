import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import database, scheduler, traffic

st.set_page_config(page_title="Phase 2 Smart Traffic Management", layout="wide")
st.title("Phase 2 Smart Traffic Management System")

def metrics_chart(rows):
    data = pd.DataFrame(rows)
    if not data.empty:
        chart_columns = ["vehicle_count", "average_speed", "average_waiting_time", "queue_length"]
        for column in chart_columns:
            if column in data:
                data[column] = pd.to_numeric(data[column], errors="coerce")
        st.plotly_chart(px.line(data, x="simulation_time", y=chart_columns, markers=False), use_container_width=True)

sumo = traffic.sumo_status(); db_status = database.status()
tab_overview, tab_traffic, tab_cpu, tab_history, tab_compare = st.tabs(["Overview", "Traffic Simulation", "CPU Scheduling", "Database and History", "Comparison and Reports"])

with tab_overview:
    a, b = st.columns(2)
    if sumo["sumo"]: a.success("SUMO is ready")
    else: a.error("SUMO is not available")
    if db_status["connected"]: b.success("MySQL is connected")
    else: b.warning("MySQL is not connected")
    latest = st.session_state.get("simulation", {}).get("summary")
    if latest is None and db_status["connected"]:
        try:
            saved_runs = database.simulation_runs(1); latest = saved_runs[0] if saved_runs else None
        except Exception: latest = None
    st.subheader("Latest simulation")
    if latest:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vehicles completed", latest["throughput"])
        c2.metric("Average speed", f"{float(latest['average_speed']):.2f} m/s")
        c3.metric("Average wait", f"{float(latest['average_waiting_time']):.2f} s")
        c4.metric("Average queue", f"{float(latest['average_queue_length']):.2f} vehicles")
        st.caption(f"Signal control: {latest['strategy'].title()} · Demand: {latest['demand']}× · Simulation time: {latest.get('duration_actual', 0)} seconds")
    else: st.info("No simulation has been run yet. Open Traffic Simulation to start one.")

with tab_traffic:
    strategy = st.selectbox("Signal control", ["fixed", "adaptive"], help="Adaptive uses live CPU scheduling decisions; fixed is the baseline.")
    if strategy == "adaptive": st.info("Adaptive scheduling is enabled. Choose an algorithm below; Round Robin also needs a time quantum.")
    else: st.caption("Fixed is the baseline. Select adaptive to use live FCFS, Priority, or Round Robin control.")
    with st.form("simulate"):
        c1, c2, c3 = st.columns(3)
        duration = c1.number_input("Duration (seconds)", 10, 3600, 300)
        demand = c2.slider("Traffic demand multiplier", 0.25, 3.0, 1.0, 0.25)
        gui = c3.checkbox("Use SUMO GUI", False, disabled=not bool(sumo["sumo_gui"]))
        if strategy == "adaptive":
            scheduling_algorithm = st.selectbox("CPU algorithm for adaptive control", traffic.SCHEDULING_ALGORITHMS, help="Uses live queue, wait, and emergency measurements every 5 seconds.")
            scheduling_quantum = st.number_input("Adaptive Round Robin quantum", 1, 20, 2) if scheduling_algorithm == "Round Robin" else 2
        else:
            scheduling_algorithm, scheduling_quantum = "FCFS", 2
        start = st.form_submit_button("Start real SUMO simulation", type="primary")
    if start:
        try:
            with st.spinner("SUMO is running through TraCI..."):
                result = traffic.run_simulation(int(duration), float(demand), strategy, gui, scheduling_algorithm, int(scheduling_quantum))
            st.session_state.simulation = result
            if db_status["connected"]:
                st.session_state.last_simulation_db_id = database.save_simulation(result, gui)
                st.success(f"Simulation finished and saved as database run #{st.session_state.last_simulation_db_id}.")
            else: st.success("Simulation finished. It was not saved because MySQL is unavailable.")
        except Exception as exc: st.error(str(exc))
    if "simulation" in st.session_state:
        result = st.session_state.simulation; st.json(result["summary"]); metrics_chart(result["snapshots"])
        st.dataframe(pd.DataFrame(result["phases"]), use_container_width=True)
        if result.get("scheduling_batches"):
            st.subheader("Live scheduling decisions")
            batch_rows = [{key: value for key, value in batch.items() if key != "tasks"} for batch in result["scheduling_batches"]]
            st.dataframe(pd.DataFrame(batch_rows), use_container_width=True)
            task_rows = [task | {"simulation_time": batch["simulation_time"], "algorithm": batch["algorithm"]} for batch in result["scheduling_batches"] for task in batch["tasks"]]
            st.caption("Tasks above were generated from measured SUMO traffic, not the fixed CPU demo.")
            st.dataframe(pd.DataFrame(task_rows), use_container_width=True)
            st.subheader("Safe TraCI signal-control actions")
            st.dataframe(pd.DataFrame(result["control_actions"]), use_container_width=True)

with tab_cpu:
    options = ["FCFS", "Priority (Non-preemptive)", "Priority (Preemptive)", "Round Robin"]
    algorithm = st.selectbox("Scheduling algorithm", options)
    quantum = st.number_input("Round Robin quantum", 1, 20, 2, disabled=algorithm != "Round Robin")
    tasks = scheduler.example_tasks(); st.dataframe(pd.DataFrame([t.__dict__ for t in tasks]), use_container_width=True)
    if st.button("Run scheduling demonstration"):
        result = scheduler.run_algorithm(algorithm, tasks, int(quantum)); st.session_state.schedule = result
        if db_status["connected"]:
            try: st.success(f"Scheduling run saved as #{database.save_schedule(result)}.")
            except Exception as exc: st.warning(f"Schedule calculated but could not be saved: {exc}")
    if "schedule" in st.session_state:
        result = st.session_state.schedule; c1, c2, c3 = st.columns(3)
        c1.metric("Average wait", result["average_waiting_time"]); c2.metric("Average turnaround", result["average_turnaround_time"]); c3.metric("Context switches", result["context_switches"])
        st.dataframe(pd.DataFrame(result["tasks"]), use_container_width=True)
        gantt = pd.DataFrame(result["timeline"]); colors = {"T1": "#4dabf7", "T2": "#228be6", "T3": "#ff8787", "T4": "#fa5252", "T5": "#69db7c", "T6": "#38d9a9"}; chart = go.Figure()
        for task_id, segments in gantt.groupby("task_id", sort=False):
            chart.add_trace(go.Bar(name=task_id, y=[task_id] * len(segments), x=(segments["end"] - segments["start"]).tolist(), base=segments["start"].tolist(), orientation="h", marker_color=colors.get(task_id, "#868e96"), customdata=segments["end"].tolist(), hovertemplate=f"Task: {task_id}<br>Start: %{{base}}<br>End: %{{customdata}}<extra></extra>"))
        chart.update_layout(title="CPU execution timeline", barmode="overlay", xaxis_title="CPU time units", yaxis_title="Task", yaxis={"categoryorder": "array", "categoryarray": [task.id for task in tasks]}, legend_title="Task")
        st.plotly_chart(chart, use_container_width=True)
    if st.checkbox("Compare all algorithms"):
        comparison = [scheduler.run_algorithm(name, tasks, int(quantum)) for name in options]
        st.dataframe(pd.DataFrame([{k: r[k] for k in ("algorithm", "average_waiting_time", "average_turnaround_time", "context_switches")} for r in comparison]), use_container_width=True)

with tab_history:
    st.write("MySQL status:", db_status["message"])
    if st.button("Initialize MySQL database and tables"):
        try: st.success(database.initialize())
        except Exception as exc: st.error("Initialization failed: " + str(exc) + ". If this specifically reports CREATE DATABASE permission, ask an administrator to create 'smart_traffic' and grant access, then try again.")
    if db_status["connected"]:
        try:
            runs = database.simulation_runs(); st.subheader("Simulation runs"); st.dataframe(pd.DataFrame(runs), use_container_width=True)
            if runs:
                run_id = st.selectbox("Inspect simulation run", [r["id"] for r in runs]); left, right = st.columns(2)
                if left.button("Load selected run"):
                    detail = database.simulation_detail(run_id); selected = detail["summary"]
                    st.subheader(f"Simulation run #{run_id}"); c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Vehicles completed", selected["throughput"]); c2.metric("Average speed", f"{float(selected['average_speed']):.2f} m/s"); c3.metric("Average wait", f"{float(selected['average_waiting_time']):.2f} s"); c4.metric("Average queue", f"{float(selected['average_queue_length']):.2f} vehicles")
                    st.caption(f"Signal control: {selected['strategy'].title()} · Demand: {selected['demand']}× · Simulation time: {selected['duration_actual']} seconds"); metrics_chart(detail["snapshots"])
                    if detail.get("scheduling_batches"): st.subheader("Saved live scheduling decisions"); st.dataframe(pd.DataFrame(detail["scheduling_batches"]), use_container_width=True)
                    if detail.get("scheduled_tasks"): st.subheader("Saved generated tasks"); st.dataframe(pd.DataFrame(detail["scheduled_tasks"]), use_container_width=True)
                    if detail.get("control_actions"): st.subheader("Saved signal-control actions"); st.dataframe(pd.DataFrame(detail["control_actions"]), use_container_width=True)
                if right.button("Delete selected simulation", type="secondary"):
                    database.delete_simulation_run(run_id); st.toast(f"Simulation run #{run_id} was deleted."); st.rerun()
            st.subheader("Scheduling history"); saved_schedules = database.scheduling_runs(); st.dataframe(pd.DataFrame(saved_schedules), use_container_width=True)
            if saved_schedules:
                schedule_id = st.selectbox("Select scheduling run to delete", [r["id"] for r in saved_schedules])
                if st.button("Delete selected scheduling run", type="secondary"):
                    database.delete_scheduling_run(schedule_id); st.toast(f"Scheduling run #{schedule_id} was deleted."); st.rerun()
            with st.expander("Delete all saved history"):
                st.warning("This permanently removes every saved simulation and scheduling run. This cannot be undone.")
                confirm_delete_all = st.checkbox("I understand that all saved history will be deleted", key="confirm_delete_all")
                if st.button("Delete all saved history", disabled=not confirm_delete_all, type="primary"):
                    sim_count, schedule_count = database.delete_all_history(); st.toast(f"Deleted {sim_count} simulation run(s) and {schedule_count} scheduling run(s)."); st.rerun()
        except Exception as exc: st.error(f"Could not load history: {exc}")

with tab_compare:
    st.info("This runs the same demand once with the fixed baseline and once with scheduler-driven adaptive control. Results below are only shown after actual SUMO executions; no values are invented.")
    duration = st.number_input("Comparison duration", 10, 1800, 300, key="compare_duration")
    demand = st.slider("Comparison demand", .25, 3.0, 1.0, .25, key="compare_demand")
    comparison_algorithm = st.selectbox("Adaptive CPU algorithm for comparison", traffic.SCHEDULING_ALGORITHMS, key="comparison_algorithm")
    comparison_quantum = st.number_input("Adaptive Round Robin quantum for comparison", 1, 20, 2, key="comparison_quantum") if comparison_algorithm == "Round Robin" else 2
    if st.button("Run fixed vs adaptive comparison"):
        rows = []
        try:
            with st.spinner("Running two real SUMO simulations..."):
                for mode in ("fixed", "adaptive"):
                    result = traffic.run_simulation(int(duration), float(demand), mode, False, comparison_algorithm, int(comparison_quantum)); rows.append(result["summary"])
                    if db_status["connected"]: database.save_simulation(result, False)
            st.dataframe(pd.DataFrame(rows)[["strategy", "scheduler_algorithm", "average_waiting_time", "average_speed", "throughput", "average_queue_length"]], use_container_width=True)
        except Exception as exc: st.error(str(exc))
    st.caption("This small synthetic junction is useful for demonstration, not a calibrated model of a real road. Randomness, route mix, and a single demand level can affect conclusions.")
