"""Data Flow and Architecture Page.

Visualizes and documents the end-to-end data pipeline from SUMO XML files
through Python TraCI, CPU OS scheduling, MySQL persistence, and the Streamlit frontend.
"""

import streamlit as st

def render_architecture_page():
    st.title("🏛️ Data Flow and System Architecture")
    st.markdown(
        "This page illustrates how **Eclipse SUMO**, **TraCI**, **OS CPU Scheduling**, "
        "**MySQL**, and **Streamlit** interconnect. Every node in this diagram corresponds "
        "to concrete Python files and classes in this repository."
    )

    # 1. End-to-End Pipeline Flow
    st.subheader("🔄 End-to-End Data Pipeline Flow")
    st.markdown(
        """
        ```mermaid
        flowchart TD
            subgraph S1 ["1. SUMO Scenario Inputs"]
                CFG["simulation.sumocfg"]
                NET["network.net.xml (J0)"]
                ROU["routes.rou.xml"]
                ADD["vehicle_types.add.xml"]
                CFG --> NET
                CFG --> ROU
                CFG --> ADD
            end

            subgraph S2 ["2. SUMO Simulation Core"]
                SUMO_PROC["SUMO Process (sumo / sumo-gui)"]
                CFG -->|Launches| SUMO_PROC
            end

            subgraph S3 ["3. Python TraCI Layer"]
                TRACI["TraCI TCP Client (simulation/traci_client.py)"]
                SUMO_PROC <-->|TCP Socket Port| TRACI
            end

            subgraph S4 ["4. Application Simulation Core"]
                MGR["SumoManager (simulation/sumo_manager.py)"]
                SIG["SignalController (simulation/signal_controller.py)"]
                MET["TrafficMetricsTracker (simulation/traffic_metrics.py)"]
                GEN["TrafficGenerator (simulation/traffic_generator.py)"]
                
                TRACI <--> MGR
                MGR --> SIG
                MGR --> MET
                GEN -->|Writes| ROU
            end

            subgraph S5 ["5. Python OS Scheduling Subsystem"]
                TASK_MODEL["TaskModel (scheduler/task_model.py)"]
                SCHED_SVC["SchedulerService (services/scheduler_service.py)"]
                FCFS["FCFS Scheduler (scheduler/fcfs.py)"]
                PRIO["Priority Scheduler (scheduler/priority.py)"]
                RR["Round Robin Scheduler (scheduler/round_robin.py)"]

                MET -.->|Synthesizes Events| SCHED_SVC
                SCHED_SVC --> TASK_MODEL
                TASK_MODEL --> FCFS
                TASK_MODEL --> PRIO
                TASK_MODEL --> RR
            end

            subgraph S6 ["6. Persistence Layer & DBMS"]
                PERSIST["PersistenceService (services/persistence_service.py)"]
                REPOS["Repositories (database/repositories.py)"]
                DBM["DatabaseManager (database/db_manager.py)"]
                MYSQL[("MySQL 8.0 Server (smart_traffic_db)")]

                MGR -->|Telemetry Snapshots| PERSIST
                SCHED_SVC -->|Task Schedules| PERSIST
                PERSIST --> REPOS
                REPOS --> DBM
                DBM <-->|mysql-connector-python| MYSQL
            end

            subgraph S7 ["7. Streamlit Presentation Layer"]
                DASH["Dashboard & Simulator Pages"]
                DBMS_EXP["DBMS Explorer Page"]
                SCHED_PAGE["OS Scheduler Page"]

                MYSQL -.->|SELECT Queries| DBMS_EXP
                MGR -.->|Live Telemetry| DASH
                SCHED_SVC -.->|Gantt & Metrics| SCHED_PAGE
            end
        ```
        """
    )

    st.divider()

    # 2. Communication Modes: In-Memory vs Persistent
    st.subheader("📡 Communication Paradigms")
    col1, col2 = st.columns(2)

    with col1:
        st.info(
            "**⚡ Direct Python Memory Communication**\n\n"
            "- **SUMO ↔ TraCI**: Low-latency binary socket protocol communicating vehicle coordinates and signal states every 1.0 second.\n"
            "- **TraCI ↔ SumoManager**: Direct Python object method calls (`client.get_vehicle_data()`, `client.simulation_step()`).\n"
            "- **SumoManager ↔ MetricsTracker**: Real-time accumulator in Python memory for instantaneous queue and speed calculations.\n"
            "- **Events ↔ OS Scheduler**: Application events translated into dataclass `Task` instances in user-space RAM."
        )

    with col2:
        st.success(
            "**💾 Permanent MySQL Database Persistence**\n\n"
            "- **Simulation Runs (`simulation_runs`)**: Run parameters, duration, totals, and timestamps.\n"
            "- **High-Frequency Telemetry (`traffic_snapshots`)**: Per-second queue counts for North, South, East, West approaches.\n"
            "- **Vehicle Lifecycles (`vehicle_observations`)**: Journey departure, arrival, and delay metrics for every vehicle.\n"
            "- **Scheduler Timelines (`scheduler_runs`, `scheduler_tasks`)**: Execution sequences, waiting times, and Gantt records."
        )

    st.divider()

    # 3. File & Class Responsibility Reference
    st.subheader("📁 Module & Function Reference Map")
    components = [
        {
            "Subsystem": "SUMO Simulation",
            "Module / File": "`simulation/sumo_manager.py`",
            "Key Class / Functions": "`SumoManager` (`start_simulation`, `step`, `run_complete`)",
            "Purpose": "Manages SUMO process lifecycle, advances simulation, orchestrates signal and metric modules."
        },
        {
            "Subsystem": "TraCI Protocol",
            "Module / File": "`simulation/traci_client.py`",
            "Key Class / Functions": "`TraCIClient` (`start`, `simulation_step`, `get_vehicle_data`, `close`)",
            "Purpose": "Low-level TCP client executing TraCI commands against SUMO."
        },
        {
            "Subsystem": "Demand Generator",
            "Module / File": "`simulation/traffic_generator.py`",
            "Key Class / Functions": "`TrafficGenerator` (`generate_demand`)",
            "Purpose": "Programmatically produces reproducible `.rou.xml` files with custom vehicles and rates."
        },
        {
            "Subsystem": "Signal Controller",
            "Module / File": "`simulation/signal_controller.py`",
            "Key Class / Functions": "`SignalController` (`update_step`, `force_phase`)",
            "Purpose": "Controls safe 6-phase cycle for Junction J0, managing clearance red and green corridors."
        },
        {
            "Subsystem": "Metrics Calculator",
            "Module / File": "`simulation/traffic_metrics.py`",
            "Key Class / Functions": "`TrafficMetricsTracker` (`record_step`, `get_summary`)",
            "Purpose": "Calculates queue lengths (< 0.1 m/s), speeds, travel times, and network throughput."
        },
        {
            "Subsystem": "OS Scheduler",
            "Module / File": "`scheduler/fcfs.py`, `priority.py`, `round_robin.py`",
            "Key Class / Functions": "`FCFSScheduler`, `PriorityScheduler`, `RoundRobinScheduler`",
            "Purpose": "Implements standard OS scheduling policies, Gantt charts, context switches, and averages."
        },
        {
            "Subsystem": "Database Layer",
            "Module / File": "`database/db_manager.py`, `repositories.py`",
            "Key Class / Functions": "`DatabaseManager`, `SimulationRepository`, `SchedulerRepository`",
            "Purpose": "Handles MySQL connections, schema DDL initialization, and parameterized CRUD transactions."
        }
    ]

    st.dataframe(components, use_container_width=True)
