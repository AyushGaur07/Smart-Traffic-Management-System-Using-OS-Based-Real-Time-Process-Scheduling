from __future__ import annotations

from dataclasses import dataclass, asdict
from collections import deque
from typing import Iterable


@dataclass(frozen=True)
class Task:
    id: str
    arrival: int
    burst: int
    priority: int
    description: str


def example_tasks() -> list[Task]:
    return [
        Task("T1", 0, 3, 2, "Collect traffic data"),
        Task("T2", 1, 2, 3, "Calculate queue lengths"),
        Task("T3", 2, 1, 1, "Update signal timing"),
        Task("T4", 3, 2, 0, "Detect emergency vehicles"),
        Task("T5", 4, 3, 2, "Save traffic metrics"),
        Task("T6", 6, 2, 4, "Generate performance reports"),
    ]


def _validate(tasks: Iterable[Task], quantum: int | None = None) -> list[Task]:
    values = list(tasks)
    if not values:
        raise ValueError("At least one scheduling task is required.")
    if len({t.id for t in values}) != len(values):
        raise ValueError("Task IDs must be unique.")
    for task in values:
        if task.arrival < 0 or task.burst <= 0:
            raise ValueError(f"Task {task.id} must have arrival >= 0 and burst > 0.")
    if quantum is not None and quantum <= 0:
        raise ValueError("Round Robin time quantum must be greater than zero.")
    return sorted(values, key=lambda t: (t.arrival, t.id))


def _result(tasks: list[Task], timeline: list[dict], first_start: dict[str, int], completion: dict[str, int]) -> dict:
    task_rows = []
    for task in tasks:
        complete = completion[task.id]
        turnaround = complete - task.arrival
        waiting = turnaround - task.burst
        task_rows.append({**asdict(task), "start_time": first_start[task.id], "completion_time": complete,
                          "turnaround_time": turnaround, "waiting_time": waiting,
                          "response_time": first_start[task.id] - task.arrival})
    switches = max(0, sum(1 for a, b in zip(timeline, timeline[1:]) if a["task_id"] != b["task_id"]))
    return {"tasks": task_rows, "timeline": timeline,
            "average_waiting_time": round(sum(x["waiting_time"] for x in task_rows) / len(task_rows), 2),
            "average_turnaround_time": round(sum(x["turnaround_time"] for x in task_rows) / len(task_rows), 2),
            "context_switches": switches}


def fcfs(tasks: Iterable[Task]) -> dict:
    tasks = _validate(tasks); time = 0; timeline = []; starts = {}; complete = {}
    for task in tasks:
        time = max(time, task.arrival); starts[task.id] = time
        timeline.append({"task_id": task.id, "start": time, "end": time + task.burst})
        time += task.burst; complete[task.id] = time
    return _result(tasks, timeline, starts, complete)


def priority_non_preemptive(tasks: Iterable[Task]) -> dict:
    tasks = _validate(tasks); pending = list(tasks); ready = []; time = 0; timeline = []; starts = {}; complete = {}
    while pending or ready:
        if not ready and pending: time = max(time, pending[0].arrival)
        while pending and pending[0].arrival <= time: ready.append(pending.pop(0))
        task = min(ready, key=lambda x: (x.priority, x.arrival, x.id)); ready.remove(task)
        starts[task.id] = time; timeline.append({"task_id": task.id, "start": time, "end": time + task.burst})
        time += task.burst; complete[task.id] = time
    return _result(tasks, timeline, starts, complete)


def priority_preemptive(tasks: Iterable[Task]) -> dict:
    tasks = _validate(tasks); remaining = {t.id: t.burst for t in tasks}; time = 0; starts = {}; complete = {}; timeline = []
    while len(complete) < len(tasks):
        ready = [t for t in tasks if t.arrival <= time and remaining[t.id] > 0]
        if not ready:
            time = min(t.arrival for t in tasks if remaining[t.id] > 0); continue
        task = min(ready, key=lambda x: (x.priority, x.arrival, x.id)); starts.setdefault(task.id, time)
        if timeline and timeline[-1]["task_id"] == task.id: timeline[-1]["end"] += 1
        else: timeline.append({"task_id": task.id, "start": time, "end": time + 1})
        remaining[task.id] -= 1; time += 1
        if remaining[task.id] == 0: complete[task.id] = time
    return _result(tasks, timeline, starts, complete)


def round_robin(tasks: Iterable[Task], quantum: int = 2) -> dict:
    tasks = _validate(tasks, quantum); remaining = {t.id: t.burst for t in tasks}; ready = deque(); index = 0; time = 0; starts = {}; complete = {}; timeline = []
    while len(complete) < len(tasks):
        if not ready and index < len(tasks) and time < tasks[index].arrival: time = tasks[index].arrival
        while index < len(tasks) and tasks[index].arrival <= time: ready.append(tasks[index]); index += 1
        task = ready.popleft(); starts.setdefault(task.id, time); run = min(quantum, remaining[task.id])
        timeline.append({"task_id": task.id, "start": time, "end": time + run})
        time += run; remaining[task.id] -= run
        while index < len(tasks) and tasks[index].arrival <= time: ready.append(tasks[index]); index += 1
        if remaining[task.id]: ready.append(task)
        else: complete[task.id] = time
    return _result(tasks, timeline, starts, complete)


def run_algorithm(name: str, tasks: Iterable[Task], quantum: int = 2) -> dict:
    methods = {"FCFS": fcfs, "Priority (Non-preemptive)": priority_non_preemptive,
               "Priority (Preemptive)": priority_preemptive}
    if name not in methods and name != "Round Robin":
        raise ValueError(f"Unknown scheduling algorithm: {name}")
    result = round_robin(tasks, quantum) if name == "Round Robin" else methods[name](tasks)
    result["algorithm"] = name; result["quantum"] = quantum if name == "Round Robin" else None
    return result


def first_scheduled_task(result: dict) -> str | None:
    timeline = result.get("timeline", [])
    return timeline[0]["task_id"] if timeline else None
