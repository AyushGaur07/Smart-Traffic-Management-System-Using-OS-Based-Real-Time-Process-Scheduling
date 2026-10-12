"""Unit tests for Traffic Metrics and Telemetry calculation."""

import pytest
from simulation.traffic_metrics import TrafficMetricsTracker

def test_metrics_tracker_registration_and_queues():
    tracker = TrafficMetricsTracker()

    active_data = {
        "veh_0": {"speed": 0.05, "waiting_time": 4.0, "edge_id": "N2J0", "route": "route_N_S", "type": "passenger"},
        "veh_1": {"speed": 12.0, "waiting_time": 0.0, "edge_id": "N2J0", "route": "route_N_S", "type": "passenger"},
        "veh_2": {"speed": 0.0, "waiting_time": 10.0, "edge_id": "E2J0", "route": "route_E_W", "type": "bus"}
    }

    snap = tracker.record_step(
        sim_time=10.0,
        active_veh_ids=["veh_0", "veh_1", "veh_2"],
        departed_veh_ids=["veh_0", "veh_1", "veh_2"],
        arrived_veh_ids=[],
        veh_data_map=active_data,
        phase_index=0,
        phase_name="North-South Green",
        corridor="North-South"
    )

    # 3 vehicles generated, 3 active, 0 completed
    assert snap["total_generated"] == 3
    assert snap["active_vehicles"] == 3
    assert snap["completed_vehicles"] == 0

    # North approach: 2 vehicles, but only veh_0 has speed < 0.1 m/s (queued)
    assert snap["north_vehicles"] == 2
    assert snap["north_queue"] == 1

    # East approach: 1 vehicle, speed 0.0 (queued)
    assert snap["east_vehicles"] == 1
    assert snap["east_queue"] == 1

    # Speeds: (0.05 + 12.0 + 0.0) / 3 = 4.016 m/s -> ~14.46 km/h
    assert snap["avg_speed_mps"] == pytest.approx(4.02, 0.05)


def test_metrics_tracker_vehicle_completion():
    tracker = TrafficMetricsTracker()

    # Step 1: Depart
    tracker.record_step(
        sim_time=0.0,
        active_veh_ids=["veh_0"],
        departed_veh_ids=["veh_0"],
        arrived_veh_ids=[],
        veh_data_map={"veh_0": {"speed": 10.0, "waiting_time": 0.0, "edge_id": "N2J0", "route": "route_N_S"}},
        phase_index=0,
        phase_name="North-South Green",
        corridor="North-South"
    )

    # Step 2: Arrive at t=20s with 5s waiting time
    snap2 = tracker.record_step(
        sim_time=20.0,
        active_veh_ids=[],
        departed_veh_ids=[],
        arrived_veh_ids=["veh_0"],
        veh_data_map={"veh_0": {"speed": 10.0, "waiting_time": 5.0, "edge_id": "J02S", "route": "route_N_S"}},
        phase_index=0,
        phase_name="North-South Green",
        corridor="North-South"
    )

    assert snap2["completed_vehicles"] == 1
    assert snap2["active_vehicles"] == 0
    # Throughput: 1 vehicle in 20s (1/3 of a min) = 3.0 veh/min
    assert snap2["throughput_per_min"] == pytest.approx(3.0, 0.1)

    summary = tracker.get_summary()
    assert summary["total_completed"] == 1
    assert summary["avg_travel_time"] == 20.0
    assert summary["avg_waiting_time"] == 5.0
    assert summary["completion_rate_pct"] == 100.0
