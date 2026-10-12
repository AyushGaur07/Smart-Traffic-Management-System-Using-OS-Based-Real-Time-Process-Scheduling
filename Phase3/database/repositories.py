"""Repository layer for parameterized MySQL operations.

Encapsulates all SQL SELECT and INSERT operations with parameterization,
transactional safety, and structured return dictionaries.
"""

from typing import Dict, List, Any, Optional
from database.db_manager import DatabaseManager

class SimulationRepository:
    """Data access repository for simulation runs and telemetric observations."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def create_simulation_run(
        self,
        junction_id: str,
        scenario_name: str,
        duration_seconds: int,
        step_length: float = 1.0
    ) -> int:
        """Insert a new simulation run record and return the generated run_id."""
        query = """
            INSERT INTO simulation_runs 
            (junction_id, scenario_name, duration_seconds, step_length, status)
            VALUES (%s, %s, %s, %s, 'RUNNING');
        """
        with self.db.cursor_scope(dictionary=False) as cursor:
            cursor.execute(query, (junction_id, scenario_name, duration_seconds, step_length))
            return cursor.lastrowid

    def update_simulation_run_completion(
        self,
        run_id: int,
        total_generated: int,
        total_completed: int,
        avg_speed_kmh: float,
        avg_waiting_time: float,
        status: str = "COMPLETED"
    ) -> None:
        """Mark a simulation run as completed with aggregate performance indicators."""
        query = """
            UPDATE simulation_runs
            SET status = %s,
                total_generated = %s,
                total_completed = %s,
                avg_speed_kmh = %s,
                avg_waiting_time = %s,
                completed_at = CURRENT_TIMESTAMP
            WHERE run_id = %s;
        """
        with self.db.cursor_scope(dictionary=False) as cursor:
            cursor.execute(
                query,
                (status, total_generated, total_completed, avg_speed_kmh, avg_waiting_time, run_id)
            )

    def insert_snapshots_batch(self, run_id: int, snapshots: List[Dict[str, Any]]) -> int:
        """Batch insert traffic telemetry snapshots."""
        if not snapshots:
            return 0

        query = """
            INSERT INTO traffic_snapshots (
                run_id, sim_time, phase_index, phase_name, active_corridor,
                active_vehicles, completed_vehicles,
                north_queue, south_queue, east_queue, west_queue,
                avg_speed_kmh, avg_waiting_time, throughput_per_min
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s
            );
        """
        params = [
            (
                run_id, s["sim_time"], s["phase_index"], s["phase_name"], s["active_corridor"],
                s["active_vehicles"], s["completed_vehicles"],
                s["north_queue"], s["south_queue"], s["east_queue"], s["west_queue"],
                s["avg_speed_kmh"], s["avg_waiting_time"], s["throughput_per_min"]
            )
            for s in snapshots
        ]

        with self.db.cursor_scope(dictionary=False) as cursor:
            cursor.executemany(query, params)
            return len(params)

    def insert_vehicle_observations_batch(self, run_id: int, observations: List[Dict[str, Any]]) -> int:
        """Batch insert individual vehicle journey records."""
        if not observations:
            return 0

        query = """
            INSERT INTO vehicle_observations (
                run_id, vehicle_id, vehicle_type, route_id,
                departure_time, arrival_time, travel_time, waiting_time, is_completed
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            );
        """
        params = [
            (
                run_id,
                obs["vehicle_id"],
                obs.get("vehicle_type", "passenger"),
                obs.get("route", "route_N_S"),
                obs.get("depart_time", 0.0),
                obs.get("arrival_time"),
                obs.get("travel_time"),
                obs.get("waiting_time", 0.0),
                1 if obs.get("arrival_time") is not None else 0
            )
            for obs in observations
        ]

        with self.db.cursor_scope(dictionary=False) as cursor:
            cursor.executemany(query, params)
            return len(params)

    def insert_signal_events_batch(self, run_id: int, events: List[Dict[str, Any]]) -> int:
        """Batch insert traffic light phase transitions."""
        if not events:
            return 0

        query = """
            INSERT INTO signal_events (
                run_id, junction_id, sim_time, old_phase_index,
                new_phase_index, phase_name, active_corridor, duration, state_str
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            );
        """
        params = [
            (
                run_id, e["junction_id"], e["sim_time"], e["old_phase_index"],
                e["new_phase_index"], e["phase_name"], e["active_corridor"],
                e["duration"], e["state_str"]
            )
            for e in events
        ]

        with self.db.cursor_scope(dictionary=False) as cursor:
            cursor.executemany(query, params)
            return len(params)

    def get_simulation_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent simulation runs ordered by start timestamp."""
        query = "SELECT * FROM simulation_runs ORDER BY run_id DESC LIMIT %s;"
        with self.db.cursor_scope(dictionary=True) as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()

    def get_snapshots_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        """Retrieve chronological snapshots for a specific simulation run."""
        query = "SELECT * FROM traffic_snapshots WHERE run_id = %s ORDER BY sim_time ASC;"
        with self.db.cursor_scope(dictionary=True) as cursor:
            cursor.execute(query, (run_id,))
            return cursor.fetchall()

    def get_observations_for_run(self, run_id: int, limit: int = 200) -> List[Dict[str, Any]]:
        """Retrieve vehicle observations for a specific run."""
        query = "SELECT * FROM vehicle_observations WHERE run_id = %s ORDER BY departure_time ASC LIMIT %s;"
        with self.db.cursor_scope(dictionary=True) as cursor:
            cursor.execute(query, (run_id, limit))
            return cursor.fetchall()

    def get_signal_events_for_run(self, run_id: int) -> List[Dict[str, Any]]:
        """Retrieve signal events for a specific run."""
        query = "SELECT * FROM signal_events WHERE run_id = %s ORDER BY sim_time ASC;"
        with self.db.cursor_scope(dictionary=True) as cursor:
            cursor.execute(query, (run_id,))
            return cursor.fetchall()


class SchedulerRepository:
    """Data access repository for user-space CPU scheduler executions."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def create_scheduler_run(
        self,
        algorithm: str,
        task_count: int,
        total_burst_time: int,
        avg_waiting_time: float,
        avg_turnaround_time: float,
        context_switches: int,
        time_quantum: Optional[int] = None,
        preemptive: bool = False
    ) -> int:
        """Insert scheduler run execution record."""
        query = """
            INSERT INTO scheduler_runs (
                algorithm, task_count, total_burst_time, avg_waiting_time,
                avg_turnaround_time, context_switches, time_quantum, preemptive
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s
            );
        """
        with self.db.cursor_scope(dictionary=False) as cursor:
            cursor.execute(
                query,
                (
                    algorithm, task_count, total_burst_time, avg_waiting_time,
                    avg_turnaround_time, context_switches, time_quantum, 1 if preemptive else 0
                )
            )
            return cursor.lastrowid

    def insert_scheduler_tasks_batch(self, scheduler_run_id: int, tasks: List[Dict[str, Any]]) -> int:
        """Batch insert evaluated tasks for a scheduler run."""
        if not tasks:
            return 0

        query = """
            INSERT INTO scheduler_tasks (
                scheduler_run_id, task_id, task_name, source_module, triggering_event,
                arrival_time, burst_time, priority, status, start_time,
                completion_time, waiting_time, turnaround_time, execution_order
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            );
        """
        params = [
            (
                scheduler_run_id,
                t["task_id"],
                t["task_name"],
                t["source_module"],
                t["triggering_event"],
                t["arrival_time"],
                t["burst_time"],
                t["priority"],
                t.get("status", "COMPLETED"),
                t.get("start_time", 0),
                t.get("completion_time", 0),
                t.get("waiting_time", 0),
                t.get("turnaround_time", 0),
                t.get("execution_order", 0)
            )
            for t in tasks
        ]

        with self.db.cursor_scope(dictionary=False) as cursor:
            cursor.executemany(query, params)
            return len(params)

    def get_scheduler_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent scheduler run records."""
        query = "SELECT * FROM scheduler_runs ORDER BY scheduler_run_id DESC LIMIT %s;"
        with self.db.cursor_scope(dictionary=True) as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()

    def get_scheduler_tasks_for_run(self, scheduler_run_id: int) -> List[Dict[str, Any]]:
        """Retrieve executed tasks for a specific scheduler run."""
        query = "SELECT * FROM scheduler_tasks WHERE scheduler_run_id = %s ORDER BY execution_order ASC;"
        with self.db.cursor_scope(dictionary=True) as cursor:
            cursor.execute(query, (scheduler_run_id,))
            return cursor.fetchall()


class PerformanceRepository:
    """Data access repository for cross-system performance comparisons."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

    def insert_performance_metric(
        self,
        scenario_name: str,
        algorithm_name: str,
        metric_name: str,
        metric_value: float,
        unit: str,
        simulation_run_id: Optional[int] = None,
        scheduler_run_id: Optional[int] = None
    ) -> int:
        """Insert a single cross-benchmark metric row."""
        query = """
            INSERT INTO performance_results (
                simulation_run_id, scheduler_run_id, scenario_name,
                algorithm_name, metric_name, metric_value, unit
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s
            );
        """
        with self.db.cursor_scope(dictionary=False) as cursor:
            cursor.execute(
                query,
                (
                    simulation_run_id, scheduler_run_id, scenario_name,
                    algorithm_name, metric_name, metric_value, unit
                )
            )
            return cursor.lastrowid

    def get_performance_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all recorded performance metrics."""
        query = "SELECT * FROM performance_results ORDER BY metric_id DESC LIMIT %s;"
        with self.db.cursor_scope(dictionary=True) as cursor:
            cursor.execute(query, (limit,))
            return cursor.fetchall()


# Metadata definitions for DBMS Explorer documentation
TABLE_DOCUMENTATION = {
    "simulation_runs": {
        "description": "Stores macro metadata for each SUMO simulation execution, including duration, vehicle counts, and aggregate traffic metrics.",
        "written_by": "services/persistence_service.py (SimulationService)",
        "read_by": "frontend/dbms_page.py, frontend/results_page.py, frontend/dashboard.py",
        "insertion_trigger": "Created when a simulation starts; updated upon simulation completion.",
        "relations": "Parent table referenced by traffic_snapshots, vehicle_observations, signal_events, performance_results."
    },
    "traffic_snapshots": {
        "description": "High-frequency periodic telemetry tracking active vehicles, approach queues (North, South, East, West), speeds, and throughput.",
        "written_by": "services/persistence_service.py (TrafficMetricsTracker)",
        "read_by": "frontend/simulator_page.py, frontend/results_page.py, frontend/dbms_page.py",
        "insertion_trigger": "Inserted at each step or periodic interval during active simulation.",
        "relations": "Foreign key (run_id) references simulation_runs(run_id) with ON DELETE CASCADE."
    },
    "vehicle_observations": {
        "description": "Fine-grained journey logs for individual vehicles, recording departure time, arrival time, total travel time, and waiting delay.",
        "written_by": "services/persistence_service.py (TraCIClient)",
        "read_by": "frontend/inputs_page.py, frontend/dbms_page.py",
        "insertion_trigger": "Saved upon vehicle arrival or at the conclusion of a simulation run.",
        "relations": "Foreign key (run_id) references simulation_runs(run_id) with ON DELETE CASCADE."
    },
    "signal_events": {
        "description": "Auditable log of traffic light transitions, recording phase name, old phase, new phase, active corridor, duration, and signal state string.",
        "written_by": "services/persistence_service.py (SignalController)",
        "read_by": "frontend/simulator_page.py, frontend/dbms_page.py",
        "insertion_trigger": "Appended whenever the traffic signal changes phase state.",
        "relations": "Foreign key (run_id) references simulation_runs(run_id) with ON DELETE CASCADE."
    },
    "scheduler_runs": {
        "description": "Evaluations of Python user-space OS scheduling algorithms (FCFS, Priority, Round Robin) with average wait, turnaround, and context switches.",
        "written_by": "services/persistence_service.py (SchedulerService)",
        "read_by": "frontend/scheduler_page.py, frontend/results_page.py, frontend/dbms_page.py",
        "insertion_trigger": "Inserted upon completion of an OS scheduler execution batch.",
        "relations": "Parent table referenced by scheduler_tasks, performance_results."
    },
    "scheduler_tasks": {
        "description": "Simulated operating system tasks created by traffic monitoring and system operations, capturing burst times, priorities, waiting, and turnaround.",
        "written_by": "services/persistence_service.py (TaskModel / Scheduler)",
        "read_by": "frontend/scheduler_page.py, frontend/dbms_page.py",
        "insertion_trigger": "Saved after scheduling simulation calculates execution order and timelines.",
        "relations": "Foreign key (scheduler_run_id) references scheduler_runs(scheduler_run_id) with ON DELETE CASCADE."
    },
    "performance_results": {
        "description": "Cross-system comparative benchmarks analyzing algorithm tradeoffs under varying traffic loads (Low, Medium, High).",
        "written_by": "services/experiment_service.py",
        "read_by": "frontend/results_page.py, frontend/dbms_page.py",
        "insertion_trigger": "Populated when comparative benchmark suites are executed.",
        "relations": "Foreign keys to simulation_runs(run_id) and scheduler_runs(scheduler_run_id)."
    }
}
