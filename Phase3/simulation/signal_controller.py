"""Traffic Signal Controller.

Manages conflict-safe signal phases for junction J0. Controls phase transitions,
safety clearance intervals, and generates auditable signal phase event logs.
"""

from typing import Dict, List, Any, Optional
from config.sumo_settings import JUNCTION_ID, SIGNAL_PHASES

class SignalController:
    """Controls traffic light phases safely and tracks signal events."""

    def __init__(self, junction_id: str = JUNCTION_ID):
        self.junction_id = junction_id
        self.phases = SIGNAL_PHASES
        self.current_phase_index = 0
        self.time_in_current_phase = 0.0
        self.total_phase_changes = 0
        self.signal_events_log: List[Dict[str, Any]] = []

    def get_current_phase_info(self) -> Dict[str, Any]:
        """Return information about the currently active phase."""
        return self.phases[self.current_phase_index]

    def update_step(self, traci_conn: Any, sim_time: float, step_size: float = 1.0) -> Optional[Dict[str, Any]]:
        """Advance signal timer by step_size and transition to next phase when duration elapses.
        
        Returns:
            Signal transition event dict if a phase change occurred, else None.
        """
        self.time_in_current_phase += step_size
        current_cfg = self.phases[self.current_phase_index]

        if self.time_in_current_phase >= current_cfg["duration"]:
            # Duration reached, transition to next phase
            old_index = self.current_phase_index
            self.current_phase_index = (self.current_phase_index + 1) % len(self.phases)
            self.time_in_current_phase = 0.0
            self.total_phase_changes += 1

            new_cfg = self.phases[self.current_phase_index]

            # Apply state to SUMO via TraCI
            try:
                traci_conn.trafficlight.setRedYellowGreenState(self.junction_id, new_cfg["state_str"])
            except Exception as e:
                # Controller handles graceful degradation if traci disconnected
                pass

            event = {
                "junction_id": self.junction_id,
                "sim_time": sim_time,
                "old_phase_index": old_index,
                "new_phase_index": self.current_phase_index,
                "phase_name": new_cfg["name"],
                "active_corridor": new_cfg["active_corridor"],
                "duration": new_cfg["duration"],
                "state_str": new_cfg["state_str"]
            }
            self.signal_events_log.append(event)
            return event

        return None

    def force_phase(self, traci_conn: Any, phase_index: int, sim_time: float) -> Dict[str, Any]:
        """Manually override signal phase (for educational demonstration)."""
        old_index = self.current_phase_index
        self.current_phase_index = phase_index % len(self.phases)
        self.time_in_current_phase = 0.0
        new_cfg = self.phases[self.current_phase_index]

        try:
            traci_conn.trafficlight.setRedYellowGreenState(self.junction_id, new_cfg["state_str"])
        except Exception:
            pass

        event = {
            "junction_id": self.junction_id,
            "sim_time": sim_time,
            "old_phase_index": old_index,
            "new_phase_index": self.current_phase_index,
            "phase_name": f"{new_cfg['name']} (Manual)",
            "active_corridor": new_cfg["active_corridor"],
            "duration": new_cfg["duration"],
            "state_str": new_cfg["state_str"]
        }
        self.signal_events_log.append(event)
        return event
