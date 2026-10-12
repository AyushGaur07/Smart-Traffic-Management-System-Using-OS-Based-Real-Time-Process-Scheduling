"""Simulation Service.

High-level interface coordinating simulation executions, TraCI stepping,
metrics collection, and database persistence.
"""

from typing import Dict, List, Any, Optional

from simulation.sumo_manager import SumoManager, SimulationState
from services.persistence_service import PersistenceService

class SimulationService:
    """Manages active simulation lifecycle and database persistence."""

    def __init__(
        self,
        sumo_manager: Optional[SumoManager] = None,
        persistence_service: Optional[PersistenceService] = None
    ):
        self.manager = sumo_manager or SumoManager()
        self.persistence = persistence_service or PersistenceService()
        self.last_saved_run_id: Optional[int] = None

    def get_status(self) -> Dict[str, Any]:
        """Return high-level operational status of the simulation."""
        return {
            "sumo_available": self.manager.is_available(),
            "state": self.manager.state,
            "current_time": self.manager.current_time,
            "max_duration": self.manager.max_duration,
            "scenario": self.manager.active_scenario,
            "mysql_connected": self.persistence.is_connected(),
            "last_saved_run_id": self.last_saved_run_id
        }

    def execute_and_persist(
        self,
        scenario: str = "Medium Demand",
        duration: int = 60,
        use_gui: bool = False,
        vehicle_count: Optional[int] = None,
        seed: int = 42,
        gui_delay_ms: int = 100,
        quit_on_end: bool = False
    ) -> Dict[str, Any]:
        """Execute a complete simulation run and persist all telemetry into MySQL."""
        # 1. Run simulation through SumoManager
        self.manager.start_simulation(
            scenario=scenario,
            duration=duration,
            use_gui=use_gui,
            vehicle_count=vehicle_count,
            seed=seed,
            gui_delay_ms=gui_delay_ms,
            quit_on_end=quit_on_end
        )

        snapshots: List[Dict[str, Any]] = []
        while self.manager.state == SimulationState.RUNNING:
            snap = self.manager.step()
            if snap:
                snapshots.append(snap)
            else:
                break

        self.manager.stop_simulation()

        summary = self.manager.metrics_tracker.get_summary()

        # 2. Persist to MySQL
        run_id = self.persistence.save_simulation_run(
            junction_id="J0",
            scenario_name=scenario,
            duration=duration,
            step_length=self.manager.step_length,
            snapshots=snapshots,
            vehicles_generated=self.manager.metrics_tracker.vehicles_generated,
            vehicles_completed=self.manager.metrics_tracker.vehicles_completed,
            signal_events=self.manager.signal_controller.signal_events_log,
            summary=summary
        )

        self.last_saved_run_id = run_id

        return {
            "run_id": run_id,
            "scenario": scenario,
            "duration": duration,
            "snapshots_count": len(snapshots),
            "summary": summary,
            "snapshots": snapshots
        }
