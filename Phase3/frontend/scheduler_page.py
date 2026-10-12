"""OS Scheduler Page.

Provides an educational user-space CPU scheduling simulation comparing
FCFS, Priority (preemptive & non-preemptive), and Round Robin algorithms
using authentic traffic management operational tasks.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from scheduler.task_model import Task, TaskStatus
from services.scheduler_service import SchedulerService

def render_scheduler_page():
    st.title("🖥️ OS CPU Scheduling Subsystem")
    st.caption("Python User-Space Educational Scheduling Simulation")

    st.warning(
        "⚠️ **Academic Disclaimer:** This subsystem is a Python user-space simulation "
        "designed for educational analysis of Operating System scheduling algorithms. "
        "It simulates CPU execution of traffic-monitoring software tasks (such as vehicle polling, "
        "signal calculation, and database persistence) and does not replace the host OS kernel scheduler."
    )

    sched_service = SchedulerService()

    # 1. Task Set Origin & Description
    st.subheader("📋 Traffic Management Task Workload")
    st.markdown(
        "These tasks represent real operations triggered by the Smart Traffic application. "
        "**Priority Convention:** Lower integer represents **HIGHER** priority (Priority 1 = Highest)."
    )

    # Let user customize or inspect tasks
    default_tasks = sched_service.generate_traffic_event_tasks()
    df_tasks = pd.DataFrame([t.to_dict() for t in default_tasks])
    cols_display = ["task_id", "task_name", "source_module", "triggering_event", "arrival_time", "burst_time", "priority"]
    st.dataframe(df_tasks[cols_display], use_container_width=True)

    st.divider()

    # 2. Algorithm Execution Controls
    st.subheader("⚡ Execute Scheduling Policy")
    col_algo, col_q, col_db = st.columns([2, 1, 1])

    with col_algo:
        selected_algo = st.selectbox(
            "Select Scheduling Algorithm",
            [
                "FCFS (First Come, First Served)",
                "Priority (Non-Preemptive)",
                "Priority (Preemptive)",
                "Round Robin"
            ]
        )

    with col_q:
        quantum = st.number_input("Time Quantum (for RR)", min_value=1, max_value=10, value=2, step=1)

    with col_db:
        save_db = st.checkbox("Persist Result to MySQL", value=True)

    btn_single, btn_compare = st.columns(2)
    run_single = btn_single.button("▶️ Run Selected Algorithm", use_container_width=True, type="primary")
    run_compare = btn_compare.button("⚖️ Compare All 3 Algorithms Side-by-Side", use_container_width=True)

    # Handle Single Algorithm Run
    if run_single:
        with st.spinner("Executing scheduler..."):
            tasks_copy = [t.copy() for t in default_tasks]
            preempt = "Preemptive" in selected_algo and not selected_algo.startswith("Round")
            res = sched_service.run_algorithm(
                algorithm_name=selected_algo,
                tasks=tasks_copy,
                time_quantum=quantum,
                preemptive_priority=preempt,
                persist_to_db=save_db
            )
            st.session_state["single_sched_res"] = res
            st.session_state.pop("compare_sched_res", None)
            st.success(f"Executed {res.algorithm}! Results displayed below.")

    # Handle Compare All Run
    if run_compare:
        with st.spinner("Comparing FCFS, Priority, and Round Robin on identical workload..."):
            tasks_copy = [t.copy() for t in default_tasks]
            compare_res = sched_service.compare_all(
                tasks=tasks_copy,
                time_quantum=quantum,
                persist_to_db=save_db
            )
            st.session_state["compare_sched_res"] = compare_res
            st.session_state.pop("single_sched_res", None)
            st.success("Comparison completed across all policies! Visual comparison displayed below.")

    # 3. Render Single Algorithm Result
    single_res = st.session_state.get("single_sched_res")
    if single_res:
        st.divider()
        st.subheader(f"📊 Results: {single_res.algorithm}")

        # Metrics KPI cards
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Average Waiting Time", f"{single_res.avg_waiting_time} ticks")
        kpi2.metric("Average Turnaround Time", f"{single_res.avg_turnaround_time} ticks")
        kpi3.metric("Context Switches", single_res.context_switches)
        kpi4.metric("Total Burst Time", f"{single_res.total_burst_time} ticks")

        # Gantt Chart Visualization
        st.subheader("📈 CPU Execution Timeline (Gantt Chart)")
        gantt_data = []
        for g in single_res.gantt_chart:
            gantt_data.append({
                "Task": f"{g.task_id}: {g.task_name}",
                "Start": g.start_time,
                "Duration": g.duration,
                "End": g.end_time,
                "TaskID": g.task_id
            })

        df_gantt = pd.DataFrame(gantt_data)
        fig_gantt = px.bar(
            df_gantt,
            x="Duration",
            y="Task",
            base="Start",
            color="TaskID",
            orientation="h",
            text="Duration",
            template="plotly_white"
        )
        fig_gantt.update_layout(
            xaxis_title="Simulation Time / CPU Ticks",
            yaxis_title="Task",
            height=320,
            showlegend=False,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_gantt, use_container_width=True)

        # Evaluated Task Details Table
        st.subheader("📝 Individual Task Completion Details")
        df_eval_tasks = pd.DataFrame([t.to_dict() for t in single_res.tasks])
        order_cols = [
            "execution_order", "task_id", "task_name", "priority",
            "arrival_time", "burst_time", "start_time", "completion_time",
            "waiting_time", "turnaround_time", "status"
        ]
        st.dataframe(df_eval_tasks[order_cols].sort_values("execution_order"), use_container_width=True)

    # 4. Render Comparative Results
    comp_res = st.session_state.get("compare_sched_res")
    if comp_res:
        st.divider()
        st.subheader("⚖️ Algorithmic Comparison (Identical Workload)")

        summary_rows = []
        for name, r in comp_res.items():
            summary_rows.append({
                "Algorithm": name,
                "Avg Waiting Time": r.avg_waiting_time,
                "Avg Turnaround Time": r.avg_turnaround_time,
                "Context Switches": r.context_switches,
                "Total Makespan": r.completion_time
            })

        df_summary = pd.DataFrame(summary_rows)
        st.dataframe(df_summary, use_container_width=True)

        # Comparative Bar Charts
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            st.subheader("⏱️ Waiting Time Comparison")
            fig_wait = px.bar(
                df_summary,
                x="Algorithm",
                y="Avg Waiting Time",
                color="Algorithm",
                text="Avg Waiting Time",
                template="plotly_white"
            )
            fig_wait.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_wait, use_container_width=True)

        with c_col2:
            st.subheader("🔄 Context Switches Comparison")
            fig_ctx = px.bar(
                df_summary,
                x="Algorithm",
                y="Context Switches",
                color="Algorithm",
                text="Context Switches",
                template="plotly_white"
            )
            fig_ctx.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_ctx, use_container_width=True)

        st.info(
            "**Academic Analysis:**\n"
            "- **FCFS** executes tasks in simple FIFO order without starvation, but suffers when long tasks arrive before short ones (Convoy Effect).\n"
            "- **Priority (Preemptive)** minimizes average waiting time by immediately serving critical tasks (Emergency corridor checks), but requires more context switches.\n"
            "- **Round Robin** provides bounded response times and fair CPU allocation, but experiences higher context-switching overhead as the time quantum shrinks."
        )
