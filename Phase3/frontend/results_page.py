"""Experiments and Results Page.

Presents multi-scenario traffic evaluations, algorithmic scheduler benchmarks,
and historical performance metrics retrieved from MySQL.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from services.experiment_service import ExperimentService
from database.db_manager import DatabaseManager
from database.repositories import PerformanceRepository, SimulationRepository, SchedulerRepository

def render_results_page():
    st.title("🧪 Experiments and Empirical Results")
    st.markdown(
        "Evaluate comparative performance across **Traffic Demand Scenarios** (Low, Medium, High) "
        "and **CPU Scheduling Policies** (FCFS, Priority, Round Robin). All results are computed "
        "by real backend execution and stored in MySQL."
    )

    exp_service = ExperimentService()
    db = DatabaseManager()
    perf_repo = PerformanceRepository(db)
    sim_repo = SimulationRepository(db)
    sched_repo = SchedulerRepository(db)

    # 1. Traffic Demand Scenarios Benchmark
    st.subheader("🚦 Experiment 1: Traffic Demand Scaling")
    st.markdown(
        "Executes 3 sequential simulations under **Low Demand** (light flow), **Medium Demand** (suburban), "
        "and **High Demand** (rush hour peak) to observe congestion onset and approach queuing."
    )

    col_btn, col_dur = st.columns([2, 1])
    with col_dur:
        bench_dur = st.slider("Duration per Scenario (s)", min_value=15, max_value=60, value=30, step=15)
    with col_btn:
        run_traffic_exp = st.button("▶️ Execute Full Traffic Benchmark Suite", use_container_width=True, type="primary")

    if run_traffic_exp:
        with st.spinner("Executing traffic scenario benchmarks across Low, Medium, High..."):
            traffic_results = exp_service.run_traffic_scenario_benchmark(duration=bench_dur)
            st.session_state["traffic_benchmark_res"] = traffic_results
            st.success("Traffic benchmark suite completed! Results updated below.")

    traffic_bench = st.session_state.get("traffic_benchmark_res")
    if traffic_bench:
        df_traffic_bench = pd.DataFrame(traffic_bench)
        st.dataframe(df_traffic_bench, use_container_width=True)

        tcol1, tcol2 = st.columns(2)
        with tcol1:
            st.subheader("🏎️ Average Network Speed by Scenario")
            fig_speed = px.bar(
                df_traffic_bench,
                x="scenario",
                y="avg_speed_kmh",
                color="scenario",
                text="avg_speed_kmh",
                template="plotly_white"
            )
            fig_speed.update_layout(height=280, showlegend=False)
            st.plotly_chart(fig_speed, use_container_width=True)

        with tcol2:
            st.subheader("🚗 Max Approach Queue by Scenario")
            fig_q = px.bar(
                df_traffic_bench,
                x="scenario",
                y="max_approach_queue",
                color="scenario",
                text="max_approach_queue",
                template="plotly_white"
            )
            fig_q.update_layout(height=280, showlegend=False)
            st.plotly_chart(fig_q, use_container_width=True)

    st.divider()

    # 2. OS CPU Schedulers Benchmark
    st.subheader("🖥️ Experiment 2: OS Scheduling Algorithm Tradeoffs")
    st.markdown(
        "Evaluates the 4 CPU scheduling policies against the standardized smart traffic task workload."
    )

    col_sbtn, col_sq = st.columns([2, 1])
    with col_sq:
        bench_quantum = st.slider("Round Robin Quantum (ticks)", min_value=1, max_value=5, value=2)
    with col_sbtn:
        run_sched_exp = st.button("▶️ Execute Scheduler Benchmark Suite", use_container_width=True)

    if run_sched_exp:
        with st.spinner("Executing scheduling benchmark suite..."):
            sched_benchmark = exp_service.run_scheduler_benchmark(time_quantum=bench_quantum)
            st.session_state["sched_benchmark_res"] = sched_benchmark
            st.success("Scheduler benchmark completed!")

    sched_bench = st.session_state.get("sched_benchmark_res")
    if sched_bench:
        df_sched_summary = pd.DataFrame(sched_bench["summary_table"])
        st.dataframe(df_sched_summary, use_container_width=True)

        scol1, scol2 = st.columns(2)
        with scol1:
            st.subheader("⏱️ Average Waiting Time")
            fig_swait = px.bar(
                df_sched_summary,
                x="algorithm",
                y="avg_waiting_time",
                color="algorithm",
                text="avg_waiting_time",
                template="plotly_white"
            )
            fig_swait.update_layout(height=280, showlegend=False)
            st.plotly_chart(fig_swait, use_container_width=True)

        with scol2:
            st.subheader("🔄 Context Switch Count")
            fig_sctx = px.bar(
                df_sched_summary,
                x="algorithm",
                y="context_switches",
                color="algorithm",
                text="context_switches",
                template="plotly_white"
            )
            fig_sctx.update_layout(height=280, showlegend=False)
            st.plotly_chart(fig_sctx, use_container_width=True)

    st.divider()

    # 3. MySQL Historical Benchmark Metrics Table
    st.subheader("💾 Historical Performance Metrics Stored in MySQL")
    try:
        perf_rows = perf_repo.get_performance_results(limit=50)
        if perf_rows:
            df_perf = pd.DataFrame(perf_rows)
            st.dataframe(df_perf, use_container_width=True)
        else:
            st.info("No records in `performance_results` table yet. Execute a benchmark suite above to populate.")
    except Exception as e:
        st.error(f"Error fetching historical metrics: {e}")
