-- ==============================================================================
-- SMART TRAFFIC SIMULATOR — RELATIONAL DATABASE SCHEMA (MySQL 8.0)
-- ==============================================================================
-- This schema establishes persistent storage for SUMO simulation runs,
-- high-frequency traffic snapshots, individual vehicle observations, signal phase
-- transition events, user-space CPU scheduler tasks, and comparative performance.
-- ==============================================================================

-- 1. SIMULATION RUNS
-- Tracks high-level metadata and aggregate outcomes of each SUMO execution.
CREATE TABLE IF NOT EXISTS simulation_runs (
    run_id INT AUTO_INCREMENT PRIMARY KEY,
    junction_id VARCHAR(32) NOT NULL DEFAULT 'J0',
    scenario_name VARCHAR(64) NOT NULL,
    duration_seconds INT NOT NULL,
    step_length DECIMAL(4, 2) NOT NULL DEFAULT 1.00,
    status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
    total_generated INT NOT NULL DEFAULT 0,
    total_completed INT NOT NULL DEFAULT 0,
    avg_speed_kmh DECIMAL(6, 2) NOT NULL DEFAULT 0.00,
    avg_waiting_time DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    INDEX idx_sim_scenario (scenario_name),
    INDEX idx_sim_started (started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. TRAFFIC SNAPSHOTS
-- Periodic telemetry capturing intersection queue lengths, active vehicles, and speeds.
CREATE TABLE IF NOT EXISTS traffic_snapshots (
    snapshot_id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL,
    sim_time DECIMAL(8, 2) NOT NULL,
    phase_index INT NOT NULL,
    phase_name VARCHAR(64) NOT NULL,
    active_corridor VARCHAR(64) NOT NULL,
    active_vehicles INT NOT NULL DEFAULT 0,
    completed_vehicles INT NOT NULL DEFAULT 0,
    north_queue INT NOT NULL DEFAULT 0,
    south_queue INT NOT NULL DEFAULT 0,
    east_queue INT NOT NULL DEFAULT 0,
    west_queue INT NOT NULL DEFAULT 0,
    avg_speed_kmh DECIMAL(6, 2) NOT NULL DEFAULT 0.00,
    avg_waiting_time DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
    throughput_per_min DECIMAL(6, 2) NOT NULL DEFAULT 0.00,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    INDEX idx_snapshot_run_time (run_id, sim_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. VEHICLE OBSERVATIONS
-- Detailed lifecycle records for each vehicle entering and traversing the junction.
CREATE TABLE IF NOT EXISTS vehicle_observations (
    obs_id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL,
    vehicle_id VARCHAR(64) NOT NULL,
    vehicle_type VARCHAR(32) NOT NULL,
    route_id VARCHAR(64) NOT NULL,
    departure_time DECIMAL(8, 2) NOT NULL,
    arrival_time DECIMAL(8, 2) NULL,
    travel_time DECIMAL(8, 2) NULL,
    waiting_time DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
    is_completed TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    INDEX idx_veh_run (run_id, vehicle_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. SIGNAL PHASE EVENTS
-- Audit log of every traffic light state change, duration, and active corridor.
CREATE TABLE IF NOT EXISTS signal_events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    run_id INT NOT NULL,
    junction_id VARCHAR(32) NOT NULL DEFAULT 'J0',
    sim_time DECIMAL(8, 2) NOT NULL,
    old_phase_index INT NOT NULL,
    new_phase_index INT NOT NULL,
    phase_name VARCHAR(64) NOT NULL,
    active_corridor VARCHAR(64) NOT NULL,
    duration INT NOT NULL,
    state_str VARCHAR(32) NOT NULL,
    triggered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id) ON DELETE CASCADE,
    INDEX idx_signal_run (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. SCHEDULER RUNS
-- Tracks executions of user-space CPU scheduling algorithms (FCFS, Priority, Round Robin).
CREATE TABLE IF NOT EXISTS scheduler_runs (
    scheduler_run_id INT AUTO_INCREMENT PRIMARY KEY,
    algorithm VARCHAR(32) NOT NULL,
    task_count INT NOT NULL DEFAULT 0,
    total_burst_time INT NOT NULL DEFAULT 0,
    avg_waiting_time DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
    avg_turnaround_time DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
    context_switches INT NOT NULL DEFAULT 0,
    time_quantum INT NULL,
    preemptive TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sched_algo (algorithm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. SCHEDULER TASKS
-- Individual simulated OS processes created by traffic monitoring and system operations.
CREATE TABLE IF NOT EXISTS scheduler_tasks (
    task_record_id INT AUTO_INCREMENT PRIMARY KEY,
    scheduler_run_id INT NOT NULL,
    task_id VARCHAR(32) NOT NULL,
    task_name VARCHAR(128) NOT NULL,
    source_module VARCHAR(64) NOT NULL,
    triggering_event VARCHAR(128) NOT NULL,
    arrival_time INT NOT NULL,
    burst_time INT NOT NULL,
    priority INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
    start_time INT NOT NULL DEFAULT 0,
    completion_time INT NOT NULL DEFAULT 0,
    waiting_time INT NOT NULL DEFAULT 0,
    turnaround_time INT NOT NULL DEFAULT 0,
    execution_order INT NOT NULL DEFAULT 0,
    FOREIGN KEY (scheduler_run_id) REFERENCES scheduler_runs(scheduler_run_id) ON DELETE CASCADE,
    INDEX idx_task_sched_run (scheduler_run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. PERFORMANCE RESULTS
-- Cross-system benchmarking linking traffic scenarios, scheduler performance, and DBMS metrics.
CREATE TABLE IF NOT EXISTS performance_results (
    metric_id INT AUTO_INCREMENT PRIMARY KEY,
    simulation_run_id INT NULL,
    scheduler_run_id INT NULL,
    scenario_name VARCHAR(64) NOT NULL,
    algorithm_name VARCHAR(32) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,
    metric_value DECIMAL(10, 2) NOT NULL,
    unit VARCHAR(32) NOT NULL,
    evaluated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (simulation_run_id) REFERENCES simulation_runs(run_id) ON DELETE SET NULL,
    FOREIGN KEY (scheduler_run_id) REFERENCES scheduler_runs(scheduler_run_id) ON DELETE SET NULL,
    INDEX idx_perf_algo (algorithm_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
