"""Integration tests for SUMO, TraCI, and Traffic Demand Generator."""

import pytest
from simulation.sumo_manager import SumoManager
from simulation.traffic_generator import TrafficGenerator

def test_traffic_generator_creates_valid_file(tmp_path):
    gen = TrafficGenerator(output_dir=tmp_path)
    res = gen.generate_demand(scenario_name="Low Demand", duration=30, vehicle_count=10, seed=123)

    assert res["vehicle_count"] == 10
    assert len(res["vehicles"]) == 10
    assert (tmp_path / "routes.rou.xml").exists()

    # Check departure order is monotonically non-decreasing
    depart_times = [v["depart"] for v in res["vehicles"]]
    assert depart_times == sorted(depart_times)


def test_sumo_manager_headless_execution():
    """Verify real SUMO process starts, advances steps via TraCI, and stops cleanly."""
    mgr = SumoManager()
    assert mgr.is_available() is True

    # Run for 8 steps
    snapshots = mgr.run_complete(scenario="Low Demand", duration=8, vehicle_count=5, seed=42)

    assert len(snapshots) == 8
    first_snap = snapshots[0]
    assert first_snap["sim_time"] == 1.0
    assert "phase_name" in first_snap
    assert "active_vehicles" in first_snap

    last_snap = snapshots[-1]
    assert last_snap["sim_time"] == 8.0
    assert mgr.state == "FINISHED"
