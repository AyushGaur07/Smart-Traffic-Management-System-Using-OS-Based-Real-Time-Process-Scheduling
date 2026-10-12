# Smart Traffic Simulator — OS Scheduling and DBMS Integration

A production-grade, educational software project integrating **Eclipse SUMO micro-simulation**, **Python TraCI**, **Operating System CPU Scheduling algorithms (FCFS, Priority, Round Robin)**, **MySQL 8.0 relational persistence**, and an interactive **Streamlit** control dashboard.

---

## 🌟 Key Features

1. **Real Traffic Micro-Simulation (SUMO & TraCI)**:
   - Conflict-safe, 4-arm junction (`J0`) with 2-lane North, South, East, and West approaches.
   - 6-phase conflict-free signal program (NS Green, NS Yellow, All-Red Clearance, EW Green, EW Yellow, All-Red Clearance).
   - Parameterized traffic demand generation across **Low**, **Medium**, and **High** demand scenarios.
   - Physical vehicle classes: passenger cars, transit buses, delivery vans, and emergency vehicles.
   - Dual execution support: command-line headless for fast automation and `sumo-gui` for visual vehicle display.

2. **Educational OS CPU Scheduling Subsystem**:
   - Written from scratch in pure Python user-space.
   - Implements **First-Come, First-Served (FCFS)**, **Priority Scheduling** (Non-Preemptive and Preemptive), and **Round Robin (RR)** with configurable quantum.
   - Dispatches authentic traffic management tasks (telemetry polling, signal actuation, database writes, emergency overrides).
   - Real-time Gantt timeline charts, context-switch counters, and exact average waiting and turnaround time math.

3. **Enterprise Database Integration (MySQL 8.0)**:
   - Full relational schema with 7 tables, primary keys, foreign keys (`ON DELETE CASCADE`), indexes, and constraints.
   - Parameterized SQL queries preventing injection vulnerabilities.
   - Built-in schema initializers with auto-creation of `smart_traffic_db`.
   - Live **DBMS Explorer** exposing real tables, column structures, row counts, foreign key constraints, and raw SQL queries.

4. **Multi-Page Streamlit Interface**:
   - **Dashboard**: System health status, live badges, quick-run actions.
   - **Traffic Simulator**: Interactive scenario execution with live approach queue charts.
   - **Inputs & Traffic Generation**: Complete visibility into raw SUMO XML files, vehicle parameters, and demand mathematics.
   - **OS CPU Scheduler**: Side-by-side policy comparisons and Gantt charts.
   - **DBMS Explorer**: Direct live MySQL table browser with pagination.
   - **Data Flow & Architecture**: Mermaid diagrams and module maps.
   - **Experiments & Results**: Multi-scenario traffic and scheduler benchmarking.
   - **Settings & Status**: Diagnostics, masked environment variables, and troubleshooting guides.

---

## 🏗️ System Architecture & Workflow

```
SUMO Scenario Files (.sumocfg, .net.xml, .rou.xml, .add.xml)
                       │
                       ▼
             SUMO Simulation Core
                       │
                       ▼ (TCP Socket Protocol)
             TraCI Python Interface
                       │
                       ▼
       Python Simulation Manager & Metrics Tracker
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  Python OS Scheduler      Persistence Service (Repositories)
(FCFS / Priority / RR)              │
          │                         ▼
          │                  MySQL 8.0 Server
          │               (7 Relational Tables)
          │                         │
          └────────────┬────────────┘
                       ▼
           Streamlit Web Dashboard
```

---

## 📋 Prerequisites & Software Installation

### 1. Python Environment
Requires Python 3.10+ (Tested on Python 3.13):
```powershell
python --version
```

### 2. Eclipse SUMO
SUMO is bundled directly via the official Python wheels (`eclipse-sumo`):
```powershell
pip install eclipse-sumo traci sumolib
```
*Note: If you already have SUMO installed globally via Windows MSI, set `$env:SUMO_HOME = "C:\Program Files (x86)\Eclipse\Sumo"`.*

### 3. MySQL Server 8.0
Ensure MySQL Server 8.0 is installed and running on your system.
In Windows PowerShell (Administrator):
```powershell
Get-Service -Name MySQL80
# If stopped, start it:
Start-Service -Name MySQL80
```

---

## 🚀 Setup & Installation Steps

### Step 1: Clone or Navigate to the Workspace
```powershell
cd c:\Users\ayush\OneDrive\Desktop\Phase3
```

### Step 2: Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment Credentials
Copy the `.env.example` file to `.env`:
```powershell
Copy-Item .env.example .env
```
Edit `.env` with your local MySQL credentials:
```ini
DB_HOST=localhost
DB_PORT=3306
DB_NAME=smart_traffic_db
DB_USER=root
DB_PASSWORD=your_mysql_password
SUMO_GUI=false
SUMO_STEP_LENGTH=1.0
```

### Step 4: Initialize MySQL Database & Tables
You can initialize the schema either through the UI (Settings or DBMS Explorer page) or directly via Python:
```powershell
python -c "from database.db_manager import DatabaseManager; db = DatabaseManager(); print(db.init_database_and_schema())"
```

---

## 🧪 Running Automated Tests

Run the comprehensive unit and integration test suite:
```powershell
python -m pytest -v
```
All 14 tests will execute, validating:
- Real MySQL connectivity and schema introspection.
- FCFS arrival ordering and idle CPU handling.
- Priority scheduling non-preemptive and preemptive preemption.
- Round Robin time-slicing and context-switch tracking.
- Traffic queue accumulation and metrics formulas.
- Real headless SUMO micro-simulation stepping via TraCI.

---

## 🖥️ Launching the Application

Start the Streamlit dashboard:
```powershell
python -m streamlit run app.py
```
*(Alternative if `streamlit` is in your Windows PATH: `streamlit run app.py`)*

The browser will automatically open at `http://localhost:8501`.

---

## 📂 Project Directory Structure

```text
smart-traffic-simulator/
│
├── app.py                      # Main Streamlit web application entry point
├── requirements.txt            # Python dependencies
├── README.md                   # Complete documentation and setup manual
├── .env.example                # Configuration template with placeholders
├── .env                        # Local environment credentials (ignored by git)
├── .gitignore                  # Git ignore rules
│
├── config/                     # Configuration subsystem
│   ├── settings.py             # Environment variables, DB settings, SUMO detection
│   └── sumo_settings.py        # Junction J0 topology, edges, routes, signal phases
│
├── frontend/                   # UI Presentation modules
│   ├── dashboard.py            # Overview dashboard, health badges, quick actions
│   ├── simulator_page.py       # Interactive simulation controls and queue charts
│   ├── inputs_page.py          # XML viewer, vehicle parameters, route generator
│   ├── scheduler_page.py       # OS CPU scheduler simulator, Gantt charts
│   ├── dbms_page.py            # Real MySQL DBMS Explorer, table browser, SQL inspector
│   ├── architecture_page.py    # Pipeline diagrams, communication maps
│   ├── results_page.py         # Multi-scenario and algorithmic benchmarks
│   └── settings_page.py        # System diagnostics and connection testers
│
├── simulation/                 # SUMO & TraCI Simulation subsystem
│   ├── sumo_manager.py         # Lifecycle manager (start, step, stop, pause)
│   ├── traci_client.py         # TCP socket wrapper for TraCI commands
│   ├── traffic_generator.py    # Programmatic route and demand generator (.rou.xml)
│   ├── traffic_metrics.py      # Queue length, speed, and delay calculators
│   └── signal_controller.py    # Conflict-safe 6-phase traffic light controller
│
├── scheduler/                  # OS CPU Scheduling subsystem
│   ├── task_model.py           # Task dataclass, lifecycle states (CREATED, READY, RUNNING, COMPLETED)
│   ├── scheduler.py            # Base scheduler, Gantt segment models, metrics calculator
│   ├── fcfs.py                 # First Come, First Served policy
│   ├── priority.py             # Priority scheduling (Non-preemptive & Preemptive)
│   └── round_robin.py          # Round Robin policy with time quantum
│
├── database/                   # Relational Persistence subsystem
│   ├── db_manager.py           # MySQL connection pooling, DDL execution, introspection
│   ├── schema.sql              # Normalized relational schema (7 tables, PKs, FKs, indexes)
│   └── repositories.py         # Parameterized CRUD repositories for MySQL
│
├── services/                   # Application Orchestration services
│   ├── simulation_service.py   # High-level simulation controller
│   ├── scheduler_service.py    # Traffic event task synthesizer and scheduler runner
│   ├── persistence_service.py  # Coordinates transactional storage to MySQL
│   └── experiment_service.py   # Automated multi-scenario benchmarking suite
│
├── sumo_files/                 # Native SUMO scenario files
│   ├── network.net.xml         # Compiled 4-arm junction network
│   ├── routes.rou.xml          # Route definitions and departure schedules
│   ├── vehicle_types.add.xml   # Physical vehicle specifications
│   ├── simulation.sumocfg      # Master SUMO configuration
│   ├── nodes.nod.xml           # Source node coordinates
│   └── edges.edg.xml           # Source edge geometry
│
├── tests/                      # Automated test suite
│   ├── test_scheduler.py       # FCFS, Priority, Round Robin unit tests
│   ├── test_database.py        # MySQL connection and repository tests
│   ├── test_metrics.py         # Traffic telemetry calculation tests
│   └── test_simulation_integration.py # Real SUMO & TraCI integration test
│
└── docs/                       # Academic Documentation
    ├── architecture.md         # Detailed system architecture specification
    ├── database_schema.md      # Relational schema dictionary & ER diagrams
    └── viva_guide.md           # Comprehensive Viva / Oral Exam preparation guide
```

---

## 🛠️ Troubleshooting Common Issues

### MySQL Connection Refused / Access Denied
1. Verify the MySQL service is running:
   ```powershell
   Get-Service -Name MySQL80
   ```
2. Verify credentials in your `.env` file match your MySQL Server root password.
3. Test connection in Python:
   ```powershell
   python -c "from database.db_manager import DatabaseManager; print(DatabaseManager().test_connection())"
   ```

### SUMO Binary Not Recognized
1. If installed via pip (`eclipse-sumo`), Python locates it automatically using `sumolib.checkBinary('sumo')`.
2. To test detection manually:
   ```powershell
   python -c "import sumolib; print(sumolib.checkBinary('sumo'))"
   ```

---

## 📜 Academic Integrity & License
This project was constructed strictly using modular, standard-library Python, verified open-source tools (Eclipse SUMO, MySQL Server), and standard Operating Systems theory. It contains no deep reinforcement learning, black-box AI models, or fake mock integrations.
