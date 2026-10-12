"""TraCI Client Interface.

Wraps the SUMO TraCI Python library to manage the TCP socket connection,
simulation stepping, vehicle introspection, and signal actuation with robust
error handling.
"""

import os
import sys
from typing import Dict, List, Any, Optional

try:
    import traci
    TRACI_AVAILABLE = True
except ImportError:
    TRACI_AVAILABLE = False


class TraCIClient:
    """Manages low-level TraCI interactions with the running SUMO process."""

    def __init__(self):
        self.is_connected = False
        self._traci = traci if TRACI_AVAILABLE else None

    def start(self, cmd: List[str], label: str = "sim_default") -> bool:
        """Start SUMO simulation and establish TraCI connection."""
        if not TRACI_AVAILABLE:
            raise RuntimeError("TraCI Python package is not installed or available.")

        try:
            # If already connected under another label, close first
            if self.is_connected:
                self.close()

            self._traci.start(cmd, label=label)
            self.is_connected = True
            return True
        except Exception as e:
            self.is_connected = False
            raise RuntimeError(f"Failed to start SUMO with TraCI: {e}") from e

    def simulation_step(self) -> float:
        """Advance the simulation by one step and return current simulation time."""
        if not self.is_connected:
            raise RuntimeError("TraCI client is not connected.")
        self._traci.simulationStep()
        return self._traci.simulation.getTime()

    def get_simulation_time(self) -> float:
        """Return the current simulation time in seconds."""
        if not self.is_connected:
            return 0.0
        return self._traci.simulation.getTime()

    def get_active_vehicle_ids(self) -> List[str]:
        """Return IDs of all vehicles currently traveling in the network."""
        if not self.is_connected:
            return []
        return list(self._traci.vehicle.getIDList())

    def get_departed_vehicle_ids(self) -> List[str]:
        """Return IDs of vehicles that departed in the current step."""
        if not self.is_connected:
            return []
        return list(self._traci.simulation.getDepartedIDList())

    def get_arrived_vehicle_ids(self) -> List[str]:
        """Return IDs of vehicles that completed trips in the current step."""
        if not self.is_connected:
            return []
        return list(self._traci.simulation.getArrivedIDList())

    def get_vehicle_data(self, vehicle_id: str) -> Dict[str, Any]:
        """Retrieve telemetry for a specific active vehicle."""
        if not self.is_connected:
            return {}
        try:
            pos = self._traci.vehicle.getPosition(vehicle_id)
            speed = self._traci.vehicle.getSpeed(vehicle_id)
            lane_id = self._traci.vehicle.getLaneID(vehicle_id)
            edge_id = self._traci.vehicle.getRoadID(vehicle_id)
            waiting_time = self._traci.vehicle.getWaitingTime(vehicle_id)
            vtype = self._traci.vehicle.getTypeID(vehicle_id)
            route_id = self._traci.vehicle.getRouteID(vehicle_id)

            return {
                "vehicle_id": vehicle_id,
                "type": vtype,
                "speed": round(speed, 2),
                "speed_kmh": round(speed * 3.6, 2),
                "position_x": round(pos[0], 2),
                "position_y": round(pos[1], 2),
                "lane_id": lane_id,
                "edge_id": edge_id,
                "waiting_time": round(waiting_time, 2),
                "route": route_id
            }
        except Exception:
            return {}

    def get_traffic_light_state(self, tl_id: str = "J0") -> str:
        """Retrieve current signal state string for a traffic light."""
        if not self.is_connected:
            return ""
        try:
            return self._traci.trafficlight.getRedYellowGreenState(tl_id)
        except Exception:
            return ""

    def set_traffic_light_state(self, tl_id: str, state_str: str) -> None:
        """Actuate traffic light to state string."""
        if self.is_connected:
            try:
                self._traci.trafficlight.setRedYellowGreenState(tl_id, state_str)
            except Exception:
                pass

    def close(self) -> None:
        """Safely terminate TraCI connection and shut down SUMO process."""
        if self.is_connected:
            try:
                self._traci.close()
            except Exception:
                pass
            finally:
                self.is_connected = False
