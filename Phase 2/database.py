from __future__ import annotations
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def _mysql():
    try:
        import mysql.connector
        return mysql.connector
    except ImportError as exc:
        raise RuntimeError("mysql-connector-python is not installed. Run: pip install -r requirements.txt") from exc

def settings() -> dict:
    return {"host": os.getenv("DB_HOST", "localhost"), "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"), "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "smart_traffic")}

def connection(include_database: bool = True):
    cfg = settings().copy()
    if not include_database: cfg.pop("database")
    return _mysql().connect(**cfg)

def status() -> dict:
    try:
        conn = connection(); conn.close()
        return {"connected": True, "message": f"Connected to MySQL database '{settings()['database']}'."}
    except Exception as exc:
        return {"connected": False, "message": str(exc)}

def initialize() -> str:
    db = settings()["database"]
    create_error = None; conn = connection(False); cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db.replace('`', '``')}`")
        conn.commit()
    except Exception as exc:
        create_error = exc
    finally: cursor.close(); conn.close()
    conn = connection(); cursor = conn.cursor()
    statements = [
        """CREATE TABLE IF NOT EXISTS simulation_runs (id BIGINT AUTO_INCREMENT PRIMARY KEY, created_at DATETIME NOT NULL, duration_requested INT NOT NULL, duration_actual INT NOT NULL, demand DECIMAL(6,2) NOT NULL, strategy VARCHAR(20) NOT NULL, gui BOOLEAN NOT NULL, throughput INT NOT NULL, average_speed DECIMAL(10,3) NOT NULL, average_waiting_time DECIMAL(10,3) NOT NULL, average_queue_length DECIMAL(10,3) NOT NULL, INDEX(created_at))""",
        """CREATE TABLE IF NOT EXISTS traffic_snapshots (id BIGINT AUTO_INCREMENT PRIMARY KEY, run_id BIGINT NOT NULL, simulation_time INT NOT NULL, vehicle_count INT NOT NULL, average_speed DECIMAL(10,3) NOT NULL, average_waiting_time DECIMAL(10,3) NOT NULL, queue_length INT NOT NULL, signal_phase INT NOT NULL, FOREIGN KEY(run_id) REFERENCES simulation_runs(id) ON DELETE CASCADE, INDEX run_time (run_id, simulation_time))""",
        """CREATE TABLE IF NOT EXISTS signal_phase_changes (id BIGINT AUTO_INCREMENT PRIMARY KEY, run_id BIGINT NOT NULL, simulation_time INT NOT NULL, phase INT NOT NULL, state VARCHAR(32) NOT NULL, FOREIGN KEY(run_id) REFERENCES simulation_runs(id) ON DELETE CASCADE, INDEX(run_id))""",
        """CREATE TABLE IF NOT EXISTS scheduling_runs (id BIGINT AUTO_INCREMENT PRIMARY KEY, created_at DATETIME NOT NULL, algorithm VARCHAR(64) NOT NULL, quantum INT NULL, average_waiting_time DECIMAL(10,2) NOT NULL, average_turnaround_time DECIMAL(10,2) NOT NULL, context_switches INT NOT NULL, INDEX(created_at))""",
        """CREATE TABLE IF NOT EXISTS scheduling_tasks (id BIGINT AUTO_INCREMENT PRIMARY KEY, scheduling_run_id BIGINT NOT NULL, task_code VARCHAR(30) NOT NULL, description VARCHAR(255) NOT NULL, arrival_time INT NOT NULL, burst_time INT NOT NULL, priority_value INT NOT NULL, start_time INT NOT NULL, completion_time INT NOT NULL, turnaround_time INT NOT NULL, waiting_time INT NOT NULL, response_time INT NOT NULL, FOREIGN KEY(scheduling_run_id) REFERENCES scheduling_runs(id) ON DELETE CASCADE, INDEX(scheduling_run_id))""",
        """CREATE TABLE IF NOT EXISTS traffic_schedule_batches (id BIGINT AUTO_INCREMENT PRIMARY KEY, simulation_run_id BIGINT NOT NULL, simulation_time INT NOT NULL, algorithm VARCHAR(64) NOT NULL, quantum INT NULL, average_waiting_time DECIMAL(10,2) NOT NULL, average_turnaround_time DECIMAL(10,2) NOT NULL, context_switches INT NOT NULL, selected_task_code VARCHAR(50) NOT NULL, FOREIGN KEY(simulation_run_id) REFERENCES simulation_runs(id) ON DELETE CASCADE, INDEX batch_time (simulation_run_id, simulation_time))""",
        """CREATE TABLE IF NOT EXISTS traffic_schedule_tasks (id BIGINT AUTO_INCREMENT PRIMARY KEY, batch_id BIGINT NOT NULL, task_code VARCHAR(50) NOT NULL, description VARCHAR(255) NOT NULL, action_name VARCHAR(50) NOT NULL, direction VARCHAR(4) NOT NULL, selected BOOLEAN NOT NULL, arrival_time INT NOT NULL, burst_time INT NOT NULL, priority_value INT NOT NULL, start_time INT NOT NULL, completion_time INT NOT NULL, turnaround_time INT NOT NULL, waiting_time INT NOT NULL, response_time INT NOT NULL, FOREIGN KEY(batch_id) REFERENCES traffic_schedule_batches(id) ON DELETE CASCADE, INDEX(batch_id))""",
        """CREATE TABLE IF NOT EXISTS signal_control_actions (id BIGINT AUTO_INCREMENT PRIMARY KEY, simulation_run_id BIGINT NOT NULL, simulation_time INT NOT NULL, task_code VARCHAR(50) NOT NULL, requested_action VARCHAR(50) NOT NULL, direction VARCHAR(4) NOT NULL, phase INT NOT NULL, action_status VARCHAR(64) NOT NULL, applied_remaining_seconds INT NULL, reason VARCHAR(255) NOT NULL, FOREIGN KEY(simulation_run_id) REFERENCES simulation_runs(id) ON DELETE CASCADE, INDEX action_time (simulation_run_id, simulation_time))""",
    ]
    try:
        for statement in statements: cursor.execute(statement)
        conn.commit()
        return "Tables are ready." if create_error else "Database and tables are ready."
    except Exception:
        conn.rollback(); raise
    finally: cursor.close(); conn.close()

def save_simulation(result: dict, gui: bool = False) -> int:
    summary = result["summary"]; conn = connection(); cur = conn.cursor()
    try:
        cur.execute("""INSERT INTO simulation_runs (created_at,duration_requested,duration_actual,demand,strategy,gui,throughput,average_speed,average_waiting_time,average_queue_length) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (datetime.now(), summary["duration_requested"], summary["duration_actual"], summary["demand"], summary["strategy"], gui, summary["throughput"], summary["average_speed"], summary["average_waiting_time"], summary["average_queue_length"]))
        run_id = cur.lastrowid
        cur.executemany("INSERT INTO traffic_snapshots (run_id,simulation_time,vehicle_count,average_speed,average_waiting_time,queue_length,signal_phase) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                        [(run_id, x["simulation_time"], x["vehicle_count"], x["average_speed"], x["average_waiting_time"], x["queue_length"], x["signal_phase"]) for x in result["snapshots"]])
        cur.executemany("INSERT INTO signal_phase_changes (run_id,simulation_time,phase,state) VALUES (%s,%s,%s,%s)",
                        [(run_id, x["simulation_time"], x["phase"], x["state"]) for x in result["phases"]])
        for batch in result.get("scheduling_batches", []):
            cur.execute("""INSERT INTO traffic_schedule_batches (simulation_run_id,simulation_time,algorithm,quantum,average_waiting_time,average_turnaround_time,context_switches,selected_task_code) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (run_id, batch["simulation_time"], batch["algorithm"], batch["quantum"],
                         batch["average_waiting_time"], batch["average_turnaround_time"],
                         batch["context_switches"], batch["selected_task_code"]))
            batch_id = cur.lastrowid
            cur.executemany("""INSERT INTO traffic_schedule_tasks (batch_id,task_code,description,action_name,direction,selected,arrival_time,burst_time,priority_value,start_time,completion_time,turnaround_time,waiting_time,response_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            [(batch_id, task["id"], task["description"], task["action"], task["direction"], task["selected"], task["arrival"], task["burst"], task["priority"], task["start_time"], task["completion_time"], task["turnaround_time"], task["waiting_time"], task["response_time"]) for task in batch["tasks"]])
        cur.executemany("""INSERT INTO signal_control_actions (simulation_run_id,simulation_time,task_code,requested_action,direction,phase,action_status,applied_remaining_seconds,reason) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        [(run_id, action["simulation_time"], action["task_code"], action["requested_action"], action["direction"], action["phase"], action["status"], action["applied_remaining_seconds"], action["reason"]) for action in result.get("control_actions", [])])
        conn.commit(); return run_id
    except Exception: conn.rollback(); raise
    finally: cur.close(); conn.close()

def save_schedule(result: dict) -> int:
    conn = connection(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO scheduling_runs (created_at,algorithm,quantum,average_waiting_time,average_turnaround_time,context_switches) VALUES (%s,%s,%s,%s,%s,%s)",
                    (datetime.now(), result["algorithm"], result["quantum"], result["average_waiting_time"], result["average_turnaround_time"], result["context_switches"]))
        run_id = cur.lastrowid
        cur.executemany("""INSERT INTO scheduling_tasks (scheduling_run_id,task_code,description,arrival_time,burst_time,priority_value,start_time,completion_time,turnaround_time,waiting_time,response_time) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        [(run_id, x["id"], x["description"], x["arrival"], x["burst"], x["priority"], x["start_time"], x["completion_time"], x["turnaround_time"], x["waiting_time"], x["response_time"]) for x in result["tasks"]])
        conn.commit(); return run_id
    except Exception: conn.rollback(); raise
    finally: cur.close(); conn.close()

def simulation_runs(limit: int = 30) -> list[dict]:
    conn = connection(); cur = conn.cursor(dictionary=True)
    try: cur.execute("SELECT * FROM simulation_runs ORDER BY id DESC LIMIT %s", (limit,)); return cur.fetchall()
    finally: cur.close(); conn.close()

def simulation_detail(run_id: int) -> dict:
    conn = connection(); cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM simulation_runs WHERE id=%s", (run_id,)); run = cur.fetchone()
        cur.execute("SELECT simulation_time,vehicle_count,average_speed,average_waiting_time,queue_length,signal_phase FROM traffic_snapshots WHERE run_id=%s ORDER BY simulation_time", (run_id,)); snapshots = cur.fetchall()
        cur.execute("SELECT simulation_time,algorithm,quantum,average_waiting_time,average_turnaround_time,context_switches,selected_task_code FROM traffic_schedule_batches WHERE simulation_run_id=%s ORDER BY simulation_time", (run_id,)); scheduling_batches = cur.fetchall()
        cur.execute("""SELECT b.simulation_time,b.algorithm,t.task_code,t.description,t.action_name,t.direction,t.selected,t.arrival_time,t.burst_time,t.priority_value,t.start_time,t.completion_time,t.turnaround_time,t.waiting_time,t.response_time FROM traffic_schedule_tasks t JOIN traffic_schedule_batches b ON b.id=t.batch_id WHERE b.simulation_run_id=%s ORDER BY b.simulation_time,t.id""", (run_id,)); scheduled_tasks = cur.fetchall()
        cur.execute("SELECT simulation_time,task_code,requested_action,direction,phase,action_status,applied_remaining_seconds,reason FROM signal_control_actions WHERE simulation_run_id=%s ORDER BY simulation_time", (run_id,)); control_actions = cur.fetchall()
        return {"summary": run, "snapshots": snapshots, "scheduling_batches": scheduling_batches,
                "scheduled_tasks": scheduled_tasks, "control_actions": control_actions}
    finally: cur.close(); conn.close()

def scheduling_runs(limit: int = 30) -> list[dict]:
    conn = connection(); cur = conn.cursor(dictionary=True)
    try: cur.execute("SELECT * FROM scheduling_runs ORDER BY id DESC LIMIT %s", (limit,)); return cur.fetchall()
    finally: cur.close(); conn.close()

def delete_simulation_run(run_id: int) -> None:
    conn = connection(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM simulation_runs WHERE id=%s", (run_id,))
        if cur.rowcount != 1:
            raise ValueError(f"Simulation run #{run_id} was not found.")
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: cur.close(); conn.close()

def delete_scheduling_run(run_id: int) -> None:
    conn = connection(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM scheduling_runs WHERE id=%s", (run_id,))
        if cur.rowcount != 1:
            raise ValueError(f"Scheduling run #{run_id} was not found.")
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: cur.close(); conn.close()

def delete_all_history() -> tuple[int, int]:
    conn = connection(); cur = conn.cursor()
    try:
        cur.execute("DELETE FROM simulation_runs")
        simulation_count = cur.rowcount
        cur.execute("DELETE FROM scheduling_runs")
        scheduling_count = cur.rowcount
        conn.commit()
        return simulation_count, scheduling_count
    except Exception:
        conn.rollback(); raise
    finally: cur.close(); conn.close()
