"""Traffic Metrics Collector and Calculator.

Maintains vehicle lifecycle tracking, approach queue lengths, waiting times,
instantaneous speeds, and aggregated network performance snapshots.
"""

from typing import Dict, List, Any, Optional
from config.sumo_settings import INBOUND_EDGES

class TrafficMetricsTracker:
    """Tracks live vehicle metrics and generates traffic snapshots."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all tracked metrics for a new simulation run."""
        self.vehicles_generated: Dict[str, Dict[str, Any]] = {}
        self.vehicles_active: Dict[str, Dict[str, Any]] = {}
        self.vehicles_completed: Dict[str, Dict[str, Any]] = {}
        self.snapshots_history: List[Dict[str, Any]] = []

    def record_step(
        self,
        sim_time: float,
        active_veh_ids: List[str],
        departed_veh_ids: List[str],
        arrived_veh_ids: List[str],
        veh_data_map: Dict[str, Dict[str, Any]],
        phase_index: int,
        phase_name: str,
        corridor: str
    ) -> Dict[str, Any]:
        """Update metrics for a single simulation time step.
        
        Args:
            sim_time: Current simulation time in seconds.
            active_veh_ids: List of IDs currently on the road.
            departed_veh_ids: List of IDs that just departed in this step.
            arrived_veh_ids: List of IDs that just completed their trip.
            veh_data_map: Dictionary mapping vehicle ID to live TraCI properties.
            phase_index: Current traffic light phase index.
            phase_name: Current phase name.
            corridor: Active corridor.
        
        Returns:
            A snapshot dictionary representing the state at sim_time.
        """
        # Register new departures
        for v_id in departed_veh_ids:
            if v_id not in self.vehicles_generated:
                self.vehicles_generated[v_id] = {
                    "vehicle_id": v_id,
                    "depart_time": sim_time,
                    "vehicle_type": veh_data_map.get(v_id, {}).get("type", "passenger"),
                    "route": veh_data_map.get(v_id, {}).get("route", "unknown")
                }

        # Update active vehicles
        current_active = {}
        for v_id in active_veh_ids:
            data = veh_data_map.get(v_id, {})
            current_active[v_id] = data

        self.vehicles_active = current_active

        # Register arrived / completed vehicles
        for v_id in arrived_veh_ids:
            gen_info = self.vehicles_generated.get(v_id, {})
            depart_time = gen_info.get("depart_time", 0.0)
            travel_time = sim_time - depart_time
            last_known = veh_data_map.get(v_id, {})

            self.vehicles_completed[v_id] = {
                "vehicle_id": v_id,
                "depart_time": depart_time,
                "arrival_time": sim_time,
                "travel_time": max(1.0, travel_time),
                "waiting_time": last_known.get("waiting_time", 0.0),
                "vehicle_type": gen_info.get("vehicle_type", "passenger")
            }

        # Approach-based queue metrics
        approach_counts = {direction: 0 for direction in INBOUND_EDGES.keys()}
        approach_waiting = {direction: 0 for direction in INBOUND_EDGES.keys()}

        speeds: List[float] = []
        waiting_times: List[float] = []

        for v_id, v in current_active.items():
            edge_id = v.get("edge_id", "")
            speed = v.get("speed", 0.0)
            wait = v.get("waiting_time", 0.0)

            speeds.append(speed)
            waiting_times.append(wait)

            for direction, in_edge in INBOUND_EDGES.items():
                if edge_id == in_edge:
                    approach_counts[direction] += 1
                    if speed < 0.1:  # Queued/stopped
                        approach_waiting[direction] += 1

        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        avg_wait = sum(waiting_times) / len(waiting_times) if waiting_times else 0.0
        max_wait = max(waiting_times) if waiting_times else 0.0

        completed_count = len(self.vehicles_completed)
        throughput_per_min = (completed_count / (sim_time / 60.0)) if sim_time > 0 else 0.0

        snapshot = {
            "sim_time": sim_time,
            "phase_index": phase_index,
            "phase_name": phase_name,
            "active_corridor": corridor,
            "total_generated": len(self.vehicles_generated),
            "active_vehicles": len(current_active),
            "completed_vehicles": completed_count,
            "north_queue": approach_waiting["North"],
            "south_queue": approach_waiting["South"],
            "east_queue": approach_waiting["East"],
            "west_queue": approach_waiting["West"],
            "north_vehicles": approach_counts["North"],
            "south_vehicles": approach_counts["South"],
            "east_vehicles": approach_counts["East"],
            "west_vehicles": approach_counts["West"],
            "avg_speed_mps": round(avg_speed, 2),
            "avg_speed_kmh": round(avg_speed * 3.6, 2),
            "avg_waiting_time": round(avg_wait, 2),
            "max_waiting_time": round(max_wait, 2),
            "throughput_per_min": round(throughput_per_min, 2)
        }

        self.snapshots_history.append(snapshot)
        return snapshot

    def get_summary(self) -> Dict[str, Any]:
        """Compute holistic summary across completed simulation."""
        completed_list = list(self.vehicles_completed.values())
        avg_travel = (
            sum(v["travel_time"] for v in completed_list) / len(completed_list)
            if completed_list else 0.0
        )
        avg_wait = (
            sum(v["waiting_time"] for v in completed_list) / len(completed_list)
            if completed_list else 0.0
        )

        return {
            "total_generated": len(self.vehicles_generated),
            "total_completed": len(self.vehicles_completed),
            "total_active_remaining": len(self.vehicles_active),
            "avg_travel_time": round(avg_travel, 2),
            "avg_waiting_time": round(avg_wait, 2),
            "completion_rate_pct": (
                round((len(self.vehicles_completed) / len(self.vehicles_generated)) * 100, 1)
                if self.vehicles_generated else 0.0
            )
        }
