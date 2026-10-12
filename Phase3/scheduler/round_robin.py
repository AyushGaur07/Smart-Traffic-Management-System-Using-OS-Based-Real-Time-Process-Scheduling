"""Round Robin (RR) CPU Scheduling Algorithm.

A preemptive, time-sliced scheduling policy that cycles ready tasks through
a FIFO ready queue, providing fair CPU sharing and bounded response times.
"""

from collections import deque
from typing import List, Optional
from scheduler.task_model import Task, TaskStatus
from scheduler.scheduler import BaseScheduler, SchedulerResult, GanttSegment

class RoundRobinScheduler(BaseScheduler):
    """Executes ready tasks in cyclic rotation bounded by a time quantum."""

    def __init__(self, time_quantum: int = 2):
        super().__init__(algorithm_name=f"Round Robin (q={time_quantum})")
        self.time_quantum = max(1, time_quantum)

    def schedule(self, tasks: List[Task]) -> SchedulerResult:
        """Run Round Robin scheduling with the configured time quantum."""
        if not tasks:
            return SchedulerResult(
                algorithm=self.algorithm_name,
                tasks=[],
                gantt_chart=[],
                total_burst_time=0,
                avg_waiting_time=0.0,
                avg_turnaround_time=0.0,
                context_switches=0,
                completion_time=0,
                time_quantum=self.time_quantum,
                preemptive=True
            )

        task_copies = [t.copy() for t in tasks]
        # Sort initially by arrival time and task_id
        task_copies.sort(key=lambda t: (t.arrival_time, t.task_id))

        total_burst = sum(t.burst_time for t in task_copies)
        current_time = 0
        context_switches = 0
        last_task_id: Optional[str] = None
        execution_order_counter = 1

        ready_queue: deque[Task] = deque()
        unadmitted: List[Task] = list(task_copies)
        completed: List[Task] = []
        gantt_chart: List[GanttSegment] = []

        while unadmitted or ready_queue:
            # If ready queue is empty, jump CPU time to next arrival
            if not ready_queue:
                next_arrival = min(t.arrival_time for t in unadmitted)
                current_time = max(current_time, next_arrival)

            # Admit all tasks that have arrived up to current_time
            arrived_now = [t for t in unadmitted if t.arrival_time <= current_time]
            for t in arrived_now:
                t.status = TaskStatus.READY
                ready_queue.append(t)
                unadmitted.remove(t)

            if not ready_queue:
                continue

            current_task = ready_queue.popleft()

            # First time task touches CPU
            if current_task.start_time is None:
                current_task.start_time = current_time
                current_task.execution_order = execution_order_counter
                execution_order_counter += 1

            if last_task_id is not None and last_task_id != current_task.task_id:
                context_switches += 1
            last_task_id = current_task.task_id

            current_task.status = TaskStatus.RUNNING

            # Slice duration: min(quantum, remaining_time)
            exec_duration = min(self.time_quantum, current_task.remaining_time)
            slice_start = current_time
            current_time += exec_duration
            current_task.remaining_time -= exec_duration

            gantt_chart.append(
                GanttSegment(
                    task_id=current_task.task_id,
                    task_name=current_task.task_name,
                    start_time=slice_start,
                    end_time=current_time,
                    duration=exec_duration
                )
            )

            # Check if any new tasks arrived DURING this time slice
            arrived_during_slice = [t for t in unadmitted if t.arrival_time <= current_time]
            for t in arrived_during_slice:
                t.status = TaskStatus.READY
                ready_queue.append(t)
                unadmitted.remove(t)

            # Check if current task finished or must be re-queued
            if current_task.remaining_time == 0:
                current_task.status = TaskStatus.COMPLETED
                current_task.completion_time = current_time
                current_task.turnaround_time = current_task.completion_time - current_task.arrival_time
                current_task.waiting_time = current_task.turnaround_time - current_task.burst_time
                completed.append(current_task)
            else:
                current_task.status = TaskStatus.READY
                ready_queue.append(current_task)

        # Restore original task list ordering
        task_id_order = {t.task_id: i for i, t in enumerate(tasks)}
        completed.sort(key=lambda t: task_id_order.get(t.task_id, 0))

        averages = self.calculate_averages(completed)

        return SchedulerResult(
            algorithm=self.algorithm_name,
            tasks=completed,
            gantt_chart=gantt_chart,
            total_burst_time=total_burst,
            avg_waiting_time=averages["avg_waiting_time"],
            avg_turnaround_time=averages["avg_turnaround_time"],
            context_switches=context_switches,
            completion_time=current_time,
            time_quantum=self.time_quantum,
            preemptive=True
        )
