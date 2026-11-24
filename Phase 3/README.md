# Phase 2 Smart Traffic Management System

A compact college demonstration project that combines a real four-way **SUMO** junction, Python **TraCI** control, MySQL history, a Streamlit dashboard, and CPU scheduling algorithms.

## What is connected now

The system has two signal-control modes:

- **fixed** keeps the original SUMO 42-second green / 3-second yellow cycle unchanged.
- **adaptive** connects real SUMO traffic to `scheduler.py`.

In adaptive mode, TraCI reads the actual queue length, per-direction waiting time, vehicle type/class, and signal state every second. Every five simulation seconds it builds a new CPU workload from that data only:

- Queue tasks are created for stopped vehicles on the north/south or east/west approach.
- Waiting-time tasks are created when a direction's average wait reaches 8 seconds.
- Emergency tasks are created when TraCI sees an emergency-class vehicle (or an ambulance/fire/police type or ID) on an incoming approach.

Select FCFS, Priority (preemptive), Priority (non-preemptive), or Round Robin in the dashboard. The selected algorithm schedules that fresh workload, and its first task becomes the requested traffic action. The simulator records every generated task, result, selected task, and action outcome.

## Signal safety

Scheduler decisions are intentionally constrained. The controller never calls TraCI `setPhase`, so it cannot jump from a red phase into a conflicting green or skip SUMO's yellow phases. It can only extend the **currently green** matching direction, and only up to 59 seconds. A selected task for a red direction is stored as `queued_for_safe_phase`; SUMO continues its normal protected transition. The fixed-time baseline is untouched.

`sumo/traffic.rou.xml` includes two real SUMO ambulance vehicles at simulation seconds 90 and 180. Run adaptive mode for at least 100 seconds to observe emergency detection. Shorter runs naturally have no emergency task.

## Project layout

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit dashboard for simulation, live scheduling decisions, history, and comparison. |
| `traffic.py` | Real SUMO/TraCI loop, dynamic task creation, safe adaptive actions, and the fixed baseline. |
| `scheduler.py` | FCFS, both priority policies, Round Robin, and the selected-first-task helper. |
| `database.py` | MySQL schema and storage for runs, snapshots, scheduler batches/tasks, and actions. |
| `sumo/traffic.net.xml` | Four-way network with traffic light `center`. |
| `sumo/traffic.rou.xml` | Passenger flows and two emergency vehicles. |

## Setup

1. Install SUMO for Windows and ensure `sumo --version` and `sumo-gui --version` work. Set `SUMO_HOME` or put SUMO's `bin` folder on `PATH` if needed.

2. Create the virtual environment and install dependencies:

   ```powershell
   cd D:\SMTS
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Configure MySQL in `.env` from `.env.example`. In the dashboard, select **Initialize MySQL database and tables** once after this update. It creates the additional scheduling and signal-action tables without removing existing data.

4. Start the dashboard:

   ```powershell
   streamlit run app.py
   ```

Use **Traffic Simulation**, select **adaptive**, then choose the CPU algorithm. The results area shows live generated tasks and safe TraCI actions. The **CPU Scheduling** tab still contains the original fixed classroom workload for demonstration; it is separate from the live SUMO workload.

## Verification

The integration was checked with the local SUMO binary and MySQL: a 120-second adaptive Priority (Preemptive) run produced 21 dynamic scheduling cycles and emergency tasks, and a 60-second adaptive Round Robin run was saved and read back from MySQL with 60 snapshots, 9 scheduler batches, and 10 safe-action records (including queued requests later applied when their direction became green).

For a repeatable local smoke test:

```powershell
.\.venv\Scripts\python.exe -c "import traffic; print(traffic.run_simulation(60, strategy='adaptive', scheduling_algorithm='FCFS')['summary'])"
```

## Limits

This is a small synthetic junction, not a calibrated road or a certified traffic controller. Real deployments require pedestrian phases, validated detectors, controller-hardware integration, and emergency-service policy approval. Compare strategies only under the same duration, demand, route mix, and SUMO version.
