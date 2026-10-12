"""First Come, First Served (FCFS) Scheduling Algorithm.

A non-preemptive scheduling policy that dispatches ready tasks strictly according
to their arrival time in the ready queue.
"""

from typing import List
from scheduler.task_model import Task, TaskStatus
from scheduler.scheduler import BaseScheduler, SchedulerResult, GanttSegment

class FCFSScheduler(BaseScheduler):
    """Executes tasks in arrival order without preemption."""

    def __init__(self):
        super().__init__(algorithm_name="FCFS")

    def schedule(self, tasks: List[Task]) -> SchedulerResult:
        """Run FCFS scheduling on a copy of the input tasks."""
        if not tasks:
            return SchedulerResult(
                algorithm=self.algorithm_name,
                tasks=[],
                gantt_chart=[],
                total_burst_time=0,
                avg_waiting_time=0.0,
                avg_turnaround_time=0.0,
                context_switches=0,
                completion_time=0
            )

        # Work on fresh copies to ensure reproducibility
        task_copies = [t.copy() for t in tasks]
        
        # Sort by arrival time, tie-breaking by original index / task_id
        sorted_tasks = sorted(task_copies, key=lambda t: (t.arrival_time, t.task_id))

        current_time = 0
        gantt_chart: List[GanttSegment] = []
        context_switches = 0
        last_task_id = None

        for order, task in enumerate(sorted_tasks, start=1):
            task.status = TaskStatus.READY

            # If CPU is idle waiting for task to arrive
            if current_time < task.arrival_time:
                current_time = task.arrival_time

            # Task starts execution
            task.status = TaskStatus.RUNNING
            task.start_time = current_time
            task.execution_order = order

            if last_task_id is not None and last_task_id != task.task_id:
                context_switches += 1
            last_task_id = task.task_id

            # Execute full burst (non-preemptive)
            start_t = current_time
            current_time += task.burst_time
            task.remaining_time = 0
            task.completion_time = current_time
            task.status = TaskStatus.COMPLETED

            # Calculate turnaround and waiting times
            task.turnaround_time = task.completion_time - task.arrival_time
            task.waiting_time = task.turnaround_time - task.burst_time

            gantt_chart.append(
                GanttSegment(
                    task_id=task.task_id,
                    task_name=task.task_name,
                    start_time=start_t,
                    end_time=current_time,
                    duration=task.burst_time
                )
            )

        averages = self.calculate_averages(sorted_tasks)
        total_burst = sum(t.burst_time for t in sorted_tasks)

        return SchedulerResult(
            algorithm=self.algorithm_name,
            tasks=sorted_tasks,
            gantt_chart=gantt_chart,
            total_burst_time=total_burst,
            avg_waiting_time=averages["avg_waiting_time"],
            avg_turnaround_time=averages["avg_turnaround_time"],
            context_switches=context_switches,
            completion_time=current_time,
            preemptive=False
        )
