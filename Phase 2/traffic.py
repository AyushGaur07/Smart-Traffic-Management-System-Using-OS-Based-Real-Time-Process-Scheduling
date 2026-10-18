from __future__ import annotations

import os
import shutil
from pathlib import Path
from statistics import mean

import scheduler

BASE_DIR = Path(__file__).resolve().parent
SUMO_CONFIG = BASE_DIR / "sumo" / "traffic.sumocfg"
TLS_ID = "center"
SCHEDULING_ALGORITHMS = (
    "FCFS", "Priority (Non-preemptive)", "Priority (Preemptive)", "Round Robin",
)
SCHEDULING_INTERVAL = 5
WAITING_TASK_THRESHOLD = 8.0
MAX_GREEN_SECONDS = 59
MIN_GREEN_SECONDS = 25


class SumoError(RuntimeError):
    pass


def find_sumo(gui: bool = False) -> str | None:
    name = "sumo-gui" if gui else "sumo"
    executable = shutil.which(name) or shutil.which(f"{name}.exe")
    if executable:
        return executable
    home = os.getenv("SUMO_HOME")
    if home:
        candidate = Path(home) / "bin" / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
    for root in (Path(r"C:/Program Files (x86)/Eclipse/Sumo"), Path(r"C:/Program Files/Eclipse/Sumo")):
        candidate = root / "bin" / f"{name}.exe"
        if candidate.exists():
            return str(candidate)
    return None


def sumo_status() -> dict:
    return {"sumo": find_sumo(False), "sumo_gui": find_sumo(True),
            "config": str(SUMO_CONFIG), "config_exists": SUMO_CONFIG.exists()}


def _traci():
    try:
        import traci
        return traci
    except ImportError as exc:
        raise SumoError("TraCI is not installed. Run: pip install -r requirements.txt") from exc


def _direction_for_edge(edge_id: str) -> str | None:
    if edge_id in {"n_in", "s_in"}:
        return "NS"
    if edge_id in {"e_in", "w_in"}:
        return "EW"
    return None


def _is_emergency_vehicle(conn, vehicle_id: str) -> bool:
    try:
        if conn.vehicle.getVehicleClass(vehicle_id) == "emergency":
            return True
    except Exception:
        pass
    try:
        label = f"{conn.vehicle.getTypeID(vehicle_id)} {vehicle_id}".lower()
    except Exception:
        return False
    return any(word in label for word in ("emergency", "ambulance", "fire", "police"))


def _traffic_measurement(conn, now: int) -> dict:
    lanes = set(conn.trafficlight.getControlledLanes(TLS_ID))
    queues = {"NS": 0, "EW": 0}
    for lane in lanes:
        direction = _direction_for_edge(conn.lane.getEdgeID(lane))
        if direction:
            queues[direction] += conn.lane.getLastStepHaltingNumber(lane)

    waits_by_direction = {"NS": [], "EW": []}
    emergency_by_direction = {"NS": [], "EW": []}
    vehicle_ids = list(conn.vehicle.getIDList())
    speeds, waits = [], []
    for vehicle_id in vehicle_ids:
        speed = conn.vehicle.getSpeed(vehicle_id)
        wait = conn.vehicle.getWaitingTime(vehicle_id)
        speeds.append(speed)
        waits.append(wait)
        direction = _direction_for_edge(conn.vehicle.getRoadID(vehicle_id))
        if direction:
            waits_by_direction[direction].append(wait)
            if _is_emergency_vehicle(conn, vehicle_id):
                emergency_by_direction[direction].append(vehicle_id)

    average_waits = {direction: round(mean(values), 3) if values else 0.0
                     for direction, values in waits_by_direction.items()}
    return {"simulation_time": now, "vehicle_count": len(vehicle_ids),
            "average_speed": round(mean(speeds), 3) if speeds else 0.0,
            "average_waiting_time": round(mean(waits), 3) if waits else 0.0,
            "queue_length": queues["NS"] + queues["EW"], "queues": queues,
            "direction_waits": average_waits, "emergency_vehicles": emergency_by_direction}


def build_traffic_tasks(measurement: dict) -> tuple[list[scheduler.Task], dict[str, dict]]:
    tasks: list[scheduler.Task] = []
    task_actions: dict[str, dict] = {}
    for direction in ("NS", "EW"):
        queue = measurement["queues"][direction]
        wait = measurement["direction_waits"][direction]
        emergency_ids = measurement["emergency_vehicles"][direction]
        if emergency_ids:
            code = f"EMERGENCY_{direction}"
            tasks.append(scheduler.Task(code, 0, 1, 0,
                        f"Emergency request for {direction}: {', '.join(emergency_ids)}"))
            task_actions[code] = {"action": "emergency_request", "direction": direction,
                                  "reason": f"Detected {len(emergency_ids)} emergency vehicle(s)"}
        if wait >= WAITING_TASK_THRESHOLD:
            code = f"WAIT_{direction}"
            priority = 1 if wait >= 20 else 2
            tasks.append(scheduler.Task(code, 0, 1, priority,
                        f"Reduce {direction} average wait of {wait:.1f} seconds"))
            task_actions[code] = {"action": "extend_green", "direction": direction,
                                  "reason": f"Average waiting time is {wait:.1f} seconds"}
        if queue > 0:
            code = f"QUEUE_{direction}"
            priority = 2 if queue >= 5 else 3
            tasks.append(scheduler.Task(code, 0, 1, priority,
                        f"Serve {direction} queue of {queue} stopped vehicle(s)"))
            task_actions[code] = {"action": "extend_green", "direction": direction,
                                  "reason": f"Queue length is {queue} vehicle(s)"}
    return tasks, task_actions


def _apply_safe_action(conn, now: int, current_phase: int, phase_started_at: int,
                       task_id: str, task_action: dict) -> dict:
    direction = task_action["direction"]
    green_phase = 0 if direction == "NS" else 2
    action = {"simulation_time": now, "task_code": task_id,
              "requested_action": task_action["action"], "direction": direction,
              "phase": current_phase, "reason": task_action["reason"],
              "status": "queued_for_safe_phase", "applied_remaining_seconds": None}
    if current_phase != green_phase:
        return action
    elapsed_green = now - phase_started_at
    allowed_remaining = max(0, MAX_GREEN_SECONDS - elapsed_green)
    if allowed_remaining <= 0:
        action["status"] = "green_cap_reached"
        return action
    current_remaining = max(0, int(round(conn.trafficlight.getNextSwitch(TLS_ID) - now)))
    requested_remaining = 15 if task_action["action"] == "emergency_request" else 10
    new_remaining = min(allowed_remaining, max(current_remaining, requested_remaining))
    if new_remaining > current_remaining:
        conn.trafficlight.setPhaseDuration(TLS_ID, new_remaining)
        action["status"] = "green_extended"
        action["applied_remaining_seconds"] = new_remaining
    else:
        action["status"] = "existing_green_is_long_enough"
        action["applied_remaining_seconds"] = current_remaining
    return action


def _run_adaptive_cycle(conn, measurement: dict, algorithm: str, quantum: int,
                        current_phase: int, phase_started_at: int) -> tuple[dict | None, dict | None]:
    tasks, actions = build_traffic_tasks(measurement)
    if not tasks:
        return None, None
    result = scheduler.run_algorithm(algorithm, tasks, quantum)
    selected_id = scheduler.first_scheduled_task(result)
    selected_action = _apply_safe_action(conn, measurement["simulation_time"], current_phase,
                                         phase_started_at, selected_id, actions[selected_id])
    batch = {"simulation_time": measurement["simulation_time"], "algorithm": algorithm,
             "quantum": result["quantum"], "average_waiting_time": result["average_waiting_time"],
             "average_turnaround_time": result["average_turnaround_time"],
             "context_switches": result["context_switches"], "selected_task_code": selected_id,
             "tasks": [{**row, "action": actions[row["id"]]["action"],
                        "direction": actions[row["id"]]["direction"],
                        "selected": row["id"] == selected_id} for row in result["tasks"]]}
    return batch, selected_action


def run_simulation(duration: int = 300, demand: float = 1.0, strategy: str = "fixed",
                   gui: bool = False, scheduling_algorithm: str = "FCFS", quantum: int = 2) -> dict:
    if duration <= 0:
        raise SumoError("Simulation duration must be greater than zero.")
    if demand <= 0:
        raise SumoError("Traffic demand multiplier must be greater than zero.")
    if strategy not in {"fixed", "adaptive"}:
        raise SumoError("Signal strategy must be 'fixed' or 'adaptive'.")
    if scheduling_algorithm not in SCHEDULING_ALGORITHMS:
        raise SumoError(f"Unknown scheduling algorithm: {scheduling_algorithm}")
    if quantum <= 0:
        raise SumoError("Round Robin time quantum must be greater than zero.")
    executable = find_sumo(gui)
    if not executable:
        raise SumoError("SUMO executable was not found. Install SUMO and add its bin folder to PATH or set SUMO_HOME.")
    if not SUMO_CONFIG.exists():
        raise SumoError(f"Missing SUMO configuration: {SUMO_CONFIG}")

    traci = _traci()
    command = [executable, "-c", str(SUMO_CONFIG), "--no-step-log", "true", "--quit-on-end", "true", "--scale", str(demand)]
    snapshots: list[dict] = []
    phases: list[dict] = []
    scheduling_batches: list[dict] = []
    control_actions: list[dict] = []
    pending_actions: dict[str, tuple[str, dict]] = {}
    previous_phase = None
    phase_started_at = 0
    started = False
    arrived_total = 0
    planned_ew_green, ns_pressure, ew_pressure, adaptive_ready = 42, 0, 0, False
    try:
        try:
            traci.start(command, label="smart_traffic")
        except Exception as exc:
            raise SumoError(f"Could not start SUMO/TraCI (a port conflict may be present): {exc}") from exc
        started = True
        conn = traci.getConnection("smart_traffic")
        if TLS_ID not in conn.trafficlight.getIDList():
            raise SumoError(f"Traffic-light ID '{TLS_ID}' was not found in the SUMO network.")
        while conn.simulation.getTime() < duration and conn.simulation.getMinExpectedNumber() > 0:
            conn.simulationStep()
            now = int(conn.simulation.getTime())
            arrived_total += conn.simulation.getArrivedNumber()
            measurement = _traffic_measurement(conn, now)
            phase = conn.trafficlight.getPhase(TLS_ID)
            if phase != previous_phase:
                phase_started_at = now
                if strategy == "adaptive" and phase in (0, 2):
                    if phase == 0:
                        ns_green = (round(84 * ns_pressure / (ns_pressure + ew_pressure))
                                    if adaptive_ready and ns_pressure + ew_pressure else 42)
                        ns_green = max(MIN_GREEN_SECONDS, min(MAX_GREEN_SECONDS, ns_green))
                        planned_ew_green, green_seconds = 84 - ns_green, ns_green
                        ns_pressure, ew_pressure, adaptive_ready = 0, 0, True
                    else:
                        green_seconds = planned_ew_green
                    conn.trafficlight.setPhaseDuration(TLS_ID, green_seconds)
                phases.append({"simulation_time": now, "phase": phase,
                               "state": conn.trafficlight.getRedYellowGreenState(TLS_ID)})
                previous_phase = phase
                if strategy == "adaptive" and phase in (0, 2):
                    green_direction = "NS" if phase == 0 else "EW"
                    pending = pending_actions.pop(green_direction, None)
                    if pending:
                        task_id, task_action = pending
                        control_actions.append(_apply_safe_action(
                            conn, now, phase, phase_started_at, task_id, task_action))
            ns_pressure += measurement["queues"]["NS"]
            ew_pressure += measurement["queues"]["EW"]
            measurement["signal_phase"] = phase
            snapshots.append({key: measurement[key] for key in ("simulation_time", "vehicle_count", "average_speed", "average_waiting_time", "queue_length", "signal_phase")})
            if strategy == "adaptive" and now % SCHEDULING_INTERVAL == 0:
                batch, action = _run_adaptive_cycle(conn, measurement, scheduling_algorithm,
                                                    quantum, phase, phase_started_at)
                if batch:
                    scheduling_batches.append(batch)
                    control_actions.append(action)
                    if action["status"] == "queued_for_safe_phase":
                        task = next(task for task in batch["tasks"] if task["id"] == action["task_code"])
                        pending_actions[action["direction"]] = (
                            action["task_code"], {"action": task["action"],
                                                  "direction": task["direction"],
                                                  "reason": action["reason"]},
                        )
    except SumoError:
        raise
    except Exception as exc:
        raise SumoError(f"SUMO simulation failed: {exc}") from exc
    finally:
        if started:
            try:
                traci.getConnection("smart_traffic").close()
            except Exception:
                pass

    summary = {"duration_requested": duration,
               "duration_actual": snapshots[-1]["simulation_time"] if snapshots else 0,
               "demand": demand, "strategy": strategy, "throughput": arrived_total,
               "average_speed": round(mean(x["average_speed"] for x in snapshots), 3) if snapshots else 0,
               "average_waiting_time": round(mean(x["average_waiting_time"] for x in snapshots), 3) if snapshots else 0,
               "average_queue_length": round(mean(x["queue_length"] for x in snapshots), 3) if snapshots else 0,
               "scheduler_algorithm": scheduling_algorithm if strategy == "adaptive" else None,
               "scheduling_cycles": len(scheduling_batches)}
    return {"summary": summary, "snapshots": snapshots, "phases": phases,
            "scheduling_batches": scheduling_batches, "control_actions": control_actions}
