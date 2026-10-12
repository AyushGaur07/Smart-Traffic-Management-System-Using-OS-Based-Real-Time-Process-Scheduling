"""Scheduler Service.

Translates traffic management events into user-space educational CPU tasks,
executes FCFS, Priority, and Round Robin algorithms, and coordinates persistence.
"""

from typing import List, Dict, Any, Optional

from scheduler.task_model import Task
from scheduler.fcfs import FCFSScheduler
from scheduler.priority import PriorityScheduler
from scheduler.round_robin import RoundRobinScheduler
from scheduler.scheduler import SchedulerResult
from database.repositories import SchedulerRepository

class SchedulerService:
    """Manages creation, execution, comparison, and storage of scheduling tasks."""

    def __init__(self, scheduler_repo: Optional[SchedulerRepository] = None):
        self.repo = scheduler_repo or SchedulerRepository()

    def generate_traffic_event_tasks(self, snapshots: Optional[List[Dict[str, Any]]] = None) -> List[Task]:
        """Synthesize realistic CPU tasks derived from smart traffic monitoring events."""
        tasks: List[Task] = []

        # Standard traffic management operational workload
        raw_task_specs = [
            (
                "T1", "Collect Traffic Telemetry", "simulation/traci_client.py",
                "Periodic Inbound Vehicle Polling", 0, 4, 2
            ),
            (
                "T2", "Evaluate Signal Transition", "simulation/signal_controller.py",
                "Phase Timer Expiration Check", 1, 3, 1
            ),
            (
                "T3", "Persist Traffic Snapshot", "services/persistence_service.py",
                "MySQL Periodic Telemetry Write", 2, 8, 4
            ),
            (
                "T4", "Emergency Corridor Actuation", "simulation/signal_controller.py",
                "Emergency Vehicle Approach Trigger", 3, 2, 1
            ),
            (
                "T5", "Compute Approach Queue Density", "simulation/traffic_metrics.py",
                "Lane Detector Congestion Analysis", 5, 5, 3
            ),
            (
                "T6", "Aggregate System Summary", "services/simulation_service.py",
                "Simulation Statistics Consolidation", 6, 6, 5
            ),
            (
                "T7", "Broadcast Traffic Advisory", "services/simulation_service.py",
                "External Highway Sign Telemetry", 8, 3, 2
            )
        ]

        for tid, name, mod, event, arr, burst, prio in raw_task_specs:
            tasks.append(
                Task(
                    task_id=tid,
                    task_name=name,
                    source_module=mod,
                    triggering_event=event,
                    arrival_time=arr,
                    burst_time=burst,
                    priority=prio
                )
            )

        return tasks

    def run_algorithm(
        self,
        algorithm_name: str,
        tasks: List[Task],
        time_quantum: int = 2,
        preemptive_priority: bool = False,
        persist_to_db: bool = True
    ) -> SchedulerResult:
        """Run a single selected scheduling algorithm and optionally persist to MySQL."""
        if algorithm_name.startswith("FCFS"):
            scheduler = FCFSScheduler()
        elif algorithm_name.startswith("Priority"):
            scheduler = PriorityScheduler(preemptive=preemptive_priority)
        elif algorithm_name.startswith("Round Robin"):
            scheduler = RoundRobinScheduler(time_quantum=time_quantum)
        else:
            raise ValueError(f"Unknown scheduling algorithm: {algorithm_name}")

        result = scheduler.schedule(tasks)

        # Persist to MySQL if requested
        if persist_to_db:
            try:
                run_id = self.repo.create_scheduler_run(
                    algorithm=result.algorithm,
                    task_count=len(result.tasks),
                    total_burst_time=result.total_burst_time,
                    avg_waiting_time=result.avg_waiting_time,
                    avg_turnaround_time=result.avg_turnaround_time,
                    context_switches=result.context_switches,
                    time_quantum=result.time_quantum,
                    preemptive=result.preemptive
                )
                self.repo.insert_scheduler_tasks_batch(run_id, [t.to_dict() for t in result.tasks])
            except Exception:
                # Handled gracefully if database is currently disconnected
                pass

        return result

    def compare_all(
        self,
        tasks: List[Task],
        time_quantum: int = 2,
        persist_to_db: bool = False
    ) -> Dict[str, SchedulerResult]:
        """Execute FCFS, Priority (Non-preemptive), Priority (Preemptive), and Round Robin on the identical task set."""
        algorithms = [
            FCFSScheduler(),
            PriorityScheduler(preemptive=False),
            PriorityScheduler(preemptive=True),
            RoundRobinScheduler(time_quantum=time_quantum)
        ]

        results = {}
        for s in algorithms:
            res = s.schedule(tasks)
            results[res.algorithm] = res
            if persist_to_db:
                try:
                    r_id = self.repo.create_scheduler_run(
                        algorithm=res.algorithm,
                        task_count=len(res.tasks),
                        total_burst_time=res.total_burst_time,
                        avg_waiting_time=res.avg_waiting_time,
                        avg_turnaround_time=res.avg_turnaround_time,
                        context_switches=res.context_switches,
                        time_quantum=res.time_quantum,
                        preemptive=res.preemptive
                    )
                    self.repo.insert_scheduler_tasks_batch(r_id, [t.to_dict() for t in res.tasks])
                except Exception:
                    pass

        return results
