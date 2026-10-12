"""Base CPU Scheduler and Result Models.

Provides core abstractions for user-space educational scheduling simulation,
Gantt timeline generation, context switch tracking, and waiting/turnaround metrics.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from scheduler.task_model import Task

@dataclass
class GanttSegment:
    """Represents an active CPU execution interval on the timeline."""
    task_id: str
    task_name: str
    start_time: int
    end_time: int
    duration: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration
        }


@dataclass
class SchedulerResult:
    """Consolidated outcome of an educational scheduler simulation run."""
    algorithm: str
    tasks: List[Task]
    gantt_chart: List[GanttSegment]
    total_burst_time: int
    avg_waiting_time: float
    avg_turnaround_time: float
    context_switches: int
    completion_time: int
    time_quantum: Optional[int] = None
    preemptive: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "task_count": len(self.tasks),
            "total_burst_time": self.total_burst_time,
            "avg_waiting_time": self.avg_waiting_time,
            "avg_turnaround_time": self.avg_turnaround_time,
            "context_switches": self.context_switches,
            "completion_time": self.completion_time,
            "time_quantum": self.time_quantum,
            "preemptive": self.preemptive,
            "tasks": [t.to_dict() for t in self.tasks],
            "gantt_chart": [g.to_dict() for g in self.gantt_chart]
        }


class BaseScheduler(ABC):
    """Abstract base class for user-space scheduling algorithms."""

    def __init__(self, algorithm_name: str):
        self.algorithm_name = algorithm_name

    @abstractmethod
    def schedule(self, tasks: List[Task]) -> SchedulerResult:
        """Execute scheduling algorithm on the provided task set."""
        pass

    @staticmethod
    def calculate_averages(tasks: List[Task]) -> Dict[str, float]:
        """Compute standard operating system metrics:
        
        - Turnaround Time = Completion Time - Arrival Time
        - Waiting Time = Turnaround Time - Burst Time
        """
        if not tasks:
            return {"avg_waiting_time": 0.0, "avg_turnaround_time": 0.0}

        total_wait = sum(t.waiting_time for t in tasks)
        total_tat = sum(t.turnaround_time for t in tasks)

        return {
            "avg_waiting_time": round(total_wait / len(tasks), 2),
            "avg_turnaround_time": round(total_tat / len(tasks), 2)
        }
