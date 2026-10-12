# Smart Traffic Simulator — Architecture & Design Document

## 1. System Overview

The **Smart Traffic Simulator** is an educational, multi-disciplinary software platform bridging discrete micro-simulation, real-time telemetry extraction, user-space CPU scheduling policies, and relational database management.

The platform demonstrates how real-world physical systems (traffic junctions) interface with systems software (operating system process schedulers) and enterprise persistence engines (relational DBMS).

```
+-----------------------------------------------------------------------------------------+
|                                STREAMLIT WEB PRESENTATION LAYER                         |
|  - Dashboard      - Traffic Simulator    - Inputs Inspector     - OS CPU Scheduler      |
|  - DBMS Explorer  - Architecture Flow    - Experiments Suite    - Diagnostics/Settings  |
+---------------------------------------+-------------------------------------------------+
                                        |
                 +----------------------+----------------------+
                 |                                             |
+----------------v-----------------------------+ +-------------v--------------------------+
|       SIMULATION & TELEMETRY SUBSYSTEM       | |       OS SCHEDULING SUBSYSTEM          |
|  - SumoManager (Lifecycle & stepping)        | |  - TaskModel (CREATED, READY, RUNNING) |
|  - TraCIClient (Binary TCP socket to SUMO)   | |  - FCFSScheduler (FIFO arrival order)  |
|  - TrafficGenerator (Deterministic .rou.xml) | |  - PriorityScheduler (Preempt & Non)   |
|  - TrafficMetricsTracker (Queues, speeds)    | |  - RoundRobinScheduler (Time Quantum)  |
|  - SignalController (6-phase conflict-free)  | |  - Gantt Timeline & Context Switches   |
+----------------------+-----------------------+ +-------------+--------------------------+
                       |                                       |
                       +-------------------+-------------------+
                                           |
                               +-----------v-----------+
                               |  PERSISTENCE SERVICE  |
                               |  (Repositories Layer) |
                               +-----------+-----------+
                                           |
                               +-----------v-----------+
                               |     MySQL 8.0 DBMS    |
                               |  - simulation_runs    |
                               |  - traffic_snapshots  |
                               |  - vehicle_obs        |
                               |  - signal_events      |
                               |  - scheduler_runs     |
                               |  - scheduler_tasks    |
                               |  - perf_results       |
                               +-----------------------+
```

---

## 2. Component Breakdown and Responsibilities

### 2.1 SUMO Scenario Definition (`sumo_files/`)
- `network.net.xml`: 4-arm junction (`J0`) compiled using SUMO's `netconvert` utility. Contains North, South, East, and West 2-lane approaches (250m long), turn connections, and traffic light cluster `J0`.
- `vehicle_types.add.xml`: Defines distinct physical characteristics (`length`, `maxSpeed`, `accel`, `decel`, `minGap`, `vClass`) for passenger cars, transit buses, delivery vans, and emergency vehicles.
- `routes.rou.xml`: 12 origin-destination routes traversing the intersection (straight, left turns, right turns).
- `simulation.sumocfg`: Master configuration XML declaring step size (1.0s), network, routes, and collision behavior.

### 2.2 TraCI Integration Layer (`simulation/traci_client.py`)
- TraCI (Traffic Control Interface) establishes a TCP socket connection directly to the running SUMO binary.
- Each simulation tick advances through `traci.simulationStep()`.
- Vehicle positions, speeds, approach lane assignments, and waiting times are queried via dedicated TraCI commands (`getIDList`, `getPosition`, `getSpeed`, `getWaitingTime`).
- Traffic light state actuation occurs via `trafficlight.setRedYellowGreenState(tl_id, state_str)`.

### 2.3 Traffic Signal Controller (`simulation/signal_controller.py`)
- Governs a safe 6-phase cycle with a total period of 72 seconds:
  1. Phase 0: North-South Green (30s) — `GGGgrrrrGGGgrrrr`
  2. Phase 1: North-South Yellow (4s) — `yyyyrrrryyyyrrrr`
  3. Phase 2: All-Red Clearance (2s) — `rrrrrrrrrrrrrrrr`
  4. Phase 3: East-West Green (30s) — `rrrrGGGgrrrrGGGg`
  5. Phase 4: East-West Yellow (4s) — `rrrryyyyrrrryyyy`
  6. Phase 5: All-Red Clearance (2s) — `rrrrrrrrrrrrrrrr`
- The all-red clearance intervals eliminate cross-traffic collisions in the intersection box.

### 2.4 OS Scheduling Subsystem (`scheduler/`)
- Pure Python user-space implementation of foundational operating system CPU scheduling algorithms:
  - **First-Come, First-Served (FCFS)**: Non-preemptive queue processing strictly in arrival order.
  - **Priority Scheduling**: Prioritizes urgent tasks (such as emergency corridor preemption and signal timeout calculation). Implements both non-preemptive and preemptive policies with arrival tie-breaking.
  - **Round Robin (RR)**: Time-sliced cyclic ready queue rotation bounded by a configurable quantum $q$.
- Tracks metrics per task: Arrival Time, Burst Time, Start Time, Completion Time, Turnaround Time ($T_{tat} = T_{comp} - T_{arr}$), Waiting Time ($T_{wait} = T_{tat} - T_{burst}$), and Context Switch counts.

### 2.5 Database Management Layer (`database/`)
- `db_manager.py`: Connection lifecycle management, automatic schema initialization from `schema.sql`, connection health checks, and schema introspection.
- `repositories.py`: Parameterized SQL repositories:
  - `SimulationRepository`: Handles `simulation_runs`, `traffic_snapshots`, `vehicle_observations`, and `signal_events`.
  - `SchedulerRepository`: Handles `scheduler_runs` and `scheduler_tasks`.
  - `PerformanceRepository`: Handles cross-system benchmarking entries.
- All SQL statements use `%s` parameterization to prevent SQL injection.

---

## 3. Communication Pathways

| Source Component | Destination Component | Protocol / Medium | Data Exchanged |
| :--- | :--- | :--- | :--- |
| `SumoManager` | SUMO Process | Subprocess CLI (`sumo.exe` / `sumo-gui.exe`) | Command-line invocation parameters (`-c simulation.sumocfg`) |
| `TraCIClient` | SUMO Process | Binary TCP Socket Protocol | Vehicle states, coordinates, speeds, signal states |
| `TrafficGenerator` | Filesystem | XML File I/O (`routes.rou.xml`) | Programmatic route paths and vehicle departure schedules |
| `SimulationService` | `PersistenceService` | In-memory Python Object references | Snapshot dictionaries, vehicle journey statistics, signal events |
| `PersistenceService` | MySQL Server | TCP Connection (`mysql-connector-python`) | Parameterized SQL `INSERT` and `UPDATE` statements |
| Streamlit UI | MySQL Server | Parameterized SQL `SELECT` | Table schema queries, row inspection, historical benchmarks |

---

## 4. Scalability: Adding Additional Junctions

The codebase is explicitly designed so additional junctions can be introduced without modifying the database schema or the OS scheduler:
1. **Network Topology**: Generate additional junction nodes (e.g., `J1`, `J2`) in `nodes.nod.xml` and connect with edge definitions in `edges.edg.xml`.
2. **Junction Identifier**: All database tables (`simulation_runs`, `signal_events`) contain a `junction_id VARCHAR(32)` column.
3. **Controller Decoupling**: `SignalController(junction_id="J1")` can be instantiated per junction.
4. **Independent Schedulers**: The CPU scheduler processes operational events regardless of whether tasks originate from Junction `J0` or Junction `J1`.
