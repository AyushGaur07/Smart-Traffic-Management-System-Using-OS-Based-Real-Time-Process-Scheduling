"""Persistence Service.

Coordinates transactional storage of simulation runs, vehicle observations,
traffic snapshots, signal events, and scheduler results to MySQL.
"""

from typing import Dict, List, Any, Optional

from database.db_manager import DatabaseManager
from database.repositories import (
    SimulationRepository,
    SchedulerRepository,
    PerformanceRepository
)

class PersistenceService:
    """Coordinates writing and reading application records to/from MySQL."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.sim_repo = SimulationRepository(self.db)
        self.sched_repo = SchedulerRepository(self.db)
        self.perf_repo = PerformanceRepository(self.db)

    def is_connected(self) -> bool:
        """Check if MySQL connection is healthy."""
        res = self.db.test_connection()
        return bool(res.get("success") and res.get("database_exists"))

    def save_simulation_run(
        self,
        junction_id: str,
        scenario_name: str,
        duration: int,
        step_length: float,
        snapshots: List[Dict[str, Any]],
        vehicles_generated: Dict[str, Dict[str, Any]],
        vehicles_completed: Dict[str, Dict[str, Any]],
        signal_events: List[Dict[str, Any]],
        summary: Dict[str, Any]
    ) -> Optional[int]:
        """Atomically persist a complete simulation run and all associated child telemetry."""
        if not self.is_connected():
            return None

        try:
            # 1. Create run record
            run_id = self.sim_repo.create_simulation_run(
                junction_id=junction_id,
                scenario_name=scenario_name,
                duration_seconds=duration,
                step_length=step_length
            )

            # 2. Insert snapshots
            if snapshots:
                self.sim_repo.insert_snapshots_batch(run_id, snapshots)

            # 3. Consolidate vehicle observations
            obs_list: List[Dict[str, Any]] = []
            for vid, g in vehicles_generated.items():
                comp = vehicles_completed.get(vid)
                obs_data = {
                    "vehicle_id": vid,
                    "vehicle_type": g.get("vehicle_type", "passenger"),
                    "route": g.get("route", "route_N_S"),
                    "depart_time": g.get("depart_time", 0.0),
                    "arrival_time": comp.get("arrival_time") if comp else None,
                    "travel_time": comp.get("travel_time") if comp else None,
                    "waiting_time": comp.get("waiting_time", 0.0) if comp else 0.0
                }
                obs_list.append(obs_data)

            if obs_list:
                self.sim_repo.insert_vehicle_observations_batch(run_id, obs_list)

            # 4. Insert signal events
            if signal_events:
                self.sim_repo.insert_signal_events_batch(run_id, signal_events)

            # 5. Finalize run record with totals
            last_speed = snapshots[-1].get("avg_speed_kmh", 0.0) if snapshots else 0.0
            avg_wait = summary.get("avg_waiting_time", 0.0)
            self.sim_repo.update_simulation_run_completion(
                run_id=run_id,
                total_generated=len(vehicles_generated),
                total_completed=len(vehicles_completed),
                avg_speed_kmh=last_speed,
                avg_waiting_time=avg_wait,
                status="COMPLETED"
            )

            return run_id
        except Exception as e:
            print(f"Persistence error: {e}")
            return None
