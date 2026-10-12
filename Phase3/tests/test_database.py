"""Database connection and repository tests."""

import pytest
from database.db_manager import DatabaseManager
from database.repositories import SimulationRepository, SchedulerRepository

def test_database_connection_real():
    """Verify live connection test succeeds against local MySQL Server."""
    db = DatabaseManager()
    res = db.test_connection()
    assert res["success"] is True
    assert "8.0" in res["server_version"]


def test_database_connection_invalid_credentials_handled_gracefully():
    """Ensure invalid credentials return structured error dictionary without unhandled crash."""
    bad_db = DatabaseManager(password="completely_wrong_password_99999")
    res = bad_db.test_connection()
    assert res["success"] is False
    assert "error_message" in res or "message" in res


def test_database_table_introspection():
    """Verify tables list and column metadata retrieval."""
    db = DatabaseManager()
    tables = db.get_tables()
    assert "simulation_runs" in tables
    assert "traffic_snapshots" in tables
    assert "scheduler_runs" in tables
    assert "scheduler_tasks" in tables

    cols = db.get_table_columns("simulation_runs")
    col_names = [c["COLUMN_NAME"] for c in cols]
    assert "run_id" in col_names
    assert "scenario_name" in col_names
    assert "duration_seconds" in col_names


def test_scheduler_repository_persistence():
    """Verify scheduler run and tasks insertion and retrieval."""
    db = DatabaseManager()
    repo = SchedulerRepository(db)

    run_id = repo.create_scheduler_run(
        algorithm="Test-Algo",
        task_count=2,
        total_burst_time=10,
        avg_waiting_time=3.5,
        avg_turnaround_time=8.5,
        context_switches=1,
        time_quantum=None,
        preemptive=False
    )
    assert run_id > 0

    tasks_data = [
        {
            "task_id": "T101",
            "task_name": "Test Task 1",
            "source_module": "tests/test_database.py",
            "triggering_event": "Unit Test Trigger",
            "arrival_time": 0,
            "burst_time": 4,
            "priority": 1,
            "status": "COMPLETED",
            "start_time": 0,
            "completion_time": 4,
            "waiting_time": 0,
            "turnaround_time": 4,
            "execution_order": 1
        }
    ]
    inserted = repo.insert_scheduler_tasks_batch(run_id, tasks_data)
    assert inserted == 1

    fetched_tasks = repo.get_scheduler_tasks_for_run(run_id)
    assert len(fetched_tasks) == 1
    assert fetched_tasks[0]["task_id"] == "T101"
