"""Priority Scheduling Algorithm (Non-preemptive and Preemptive).

Selects the task with the highest priority (lowest numeric value) from the ready pool.
Tie-breaking rule: Earliest arrival time, followed by lexicographical task ID.
"""

from typing import List, Optional
from scheduler.task_model import Task, TaskStatus
from scheduler.scheduler import BaseScheduler, SchedulerResult, GanttSegment

class PriorityScheduler(BaseScheduler):
    """Executes tasks based on priority values.
    
    Priority Convention:
        Lower integer indicates HIGHER priority (1 is highest).
        Tie-breaking: Earliest arrival time (FCFS).
    """

    def __init__(self, preemptive: bool = False):
        algo_name = "Priority (Preemptive)" if preemptive else "Priority (Non-Preemptive)"
        super().__init__(algorithm_name=algo_name)
        self.preemptive = preemptive

    def schedule(self, tasks: List[Task]) -> SchedulerResult:
        """Run priority scheduling."""
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
                preemptive=self.preemptive
            )

        if self.preemptive:
            return self._schedule_preemptive(tasks)
        return self._schedule_non_preemptive(tasks)

    def _schedule_non_preemptive(self, tasks: List[Task]) -> SchedulerResult:
        """Non-preemptive priority dispatching."""
        task_copies = [t.copy() for t in tasks]
        completed: List[Task] = []
        gantt_chart: List[GanttSegment] = []
        
        current_time = 0
        context_switches = 0
        last_task_id = None
        execution_order = 1

        uncompleted = list(task_copies)

        while uncompleted:
            # Find eligible ready tasks (arrival_time <= current_time)
            ready_pool = [t for t in uncompleted if t.arrival_time <= current_time]

            if not ready_pool:
                # CPU is idle until next task arrival
                next_arrival = min(t.arrival_time for t in uncompleted)
                current_time = next_arrival
                continue

            # Select task with lowest numeric priority, tie-broken by arrival time and task_id
            selected_task = min(
                ready_pool,
                key=lambda t: (t.priority, t.arrival_time, t.task_id)
            )

            # Mark ready and then running
            selected_task.status = TaskStatus.RUNNING
            if selected_task.start_time is None:
                selected_task.start_time = current_time
            selected_task.execution_order = execution_order
            execution_order += 1

            if last_task_id is not None and last_task_id != selected_task.task_id:
                context_switches += 1
            last_task_id = selected_task.task_id

            # Execute to completion
            start_t = current_time
            current_time += selected_task.burst_time
            selected_task.remaining_time = 0
            selected_task.completion_time = current_time
            selected_task.status = TaskStatus.COMPLETED

            # Turnaround and waiting
            selected_task.turnaround_time = selected_task.completion_time - selected_task.arrival_time
            selected_task.waiting_time = selected_task.turnaround_time - selected_task.burst_time

            gantt_chart.append(
                GanttSegment(
                    task_id=selected_task.task_id,
                    task_name=selected_task.task_name,
                    start_time=start_t,
                    end_time=current_time,
                    duration=selected_task.burst_time
                )
            )

            uncompleted.remove(selected_task)
            completed.append(selected_task)

        # Restore original task sorting for consistent reporting
        task_id_order = {t.task_id: i for i, t in enumerate(tasks)}
        completed.sort(key=lambda t: task_id_order.get(t.task_id, 0))

        averages = self.calculate_averages(completed)
        total_burst = sum(t.burst_time for t in completed)

        return SchedulerResult(
            algorithm=self.algorithm_name,
            tasks=completed,
            gantt_chart=gantt_chart,
            total_burst_time=total_burst,
            avg_waiting_time=averages["avg_waiting_time"],
            avg_turnaround_time=averages["avg_turnaround_time"],
            context_switches=context_switches,
            completion_time=current_time,
            preemptive=False
        )

    def _schedule_preemptive(self, tasks: List[Task]) -> SchedulerResult:
        """Preemptive priority scheduling simulation."""
        task_copies = [t.copy() for t in tasks]
        total_burst = sum(t.burst_time for t in task_copies)
        
        current_time = 0
        completed_tasks: List[Task] = []
        gantt_chart: List[GanttSegment] = []
        context_switches = 0
        last_task_id: Optional[str] = None
        execution_order_counter = 1

        uncompleted = list(task_copies)

        current_segment_task: Optional[Task] = None
        segment_start_time = 0

        while uncompleted:
            ready_pool = [t for t in uncompleted if t.arrival_time <= current_time]

            if not ready_pool:
                if current_segment_task is not None:
                    # Close existing segment before idle jump
                    gantt_chart.append(
                        GanttSegment(
                            task_id=current_segment_task.task_id,
                            task_name=current_segment_task.task_name,
                            start_time=segment_start_time,
                            end_time=current_time,
                            duration=current_time - segment_start_time
                        )
                    )
                    current_segment_task = None

                next_arrival = min(t.arrival_time for t in uncompleted)
                current_time = next_arrival
                continue

            # Pick highest priority ready task
            best_task = min(
                ready_pool,
                key=lambda t: (t.priority, t.arrival_time, t.task_id)
            )

            # Check if context switch occurred
            if current_segment_task is not None and current_segment_task.task_id != best_task.task_id:
                # Record the completed interval for the preempted task
                gantt_chart.append(
                    GanttSegment(
                        task_id=current_segment_task.task_id,
                        task_name=current_segment_task.task_name,
                        start_time=segment_start_time,
                        end_time=current_time,
                        duration=current_time - segment_start_time
                    )
                )
                current_segment_task.status = TaskStatus.READY
                current_segment_task = None
                context_switches += 1

            if current_segment_task is None:
                current_segment_task = best_task
                segment_start_time = current_time
                if best_task.start_time is None:
                    best_task.start_time = current_time
                    best_task.execution_order = execution_order_counter
                    execution_order_counter += 1
                best_task.status = TaskStatus.RUNNING
                if last_task_id is not None and last_task_id != best_task.task_id:
                    context_switches += 1
                last_task_id = best_task.task_id

            # Determine next critical event: either task finishes or a new higher priority task arrives
            # Future arrivals that have higher priority than current_segment_task
            future_higher_arrivals = [
                t.arrival_time for t in uncompleted
                if t.arrival_time > current_time and t.priority < best_task.priority
            ]
            
            time_to_completion = best_task.remaining_time
            if future_higher_arrivals:
                next_preempt_time = min(future_higher_arrivals)
                time_step = min(time_to_completion, next_preempt_time - current_time)
            else:
                time_step = time_to_completion

            # Advance time
            current_time += time_step
            best_task.remaining_time -= time_step

            if best_task.remaining_time == 0:
                # Task completed
                best_task.completion_time = current_time
                best_task.turnaround_time = best_task.completion_time - best_task.arrival_time
                best_task.waiting_time = best_task.turnaround_time - best_task.burst_time
                best_task.status = TaskStatus.COMPLETED
                
                gantt_chart.append(
                    GanttSegment(
                        task_id=best_task.task_id,
                        task_name=best_task.task_name,
                        start_time=segment_start_time,
                        end_time=current_time,
                        duration=current_time - segment_start_time
                    )
                )
                current_segment_task = None
                uncompleted.remove(best_task)
                completed_tasks.append(best_task)

        # Restore original task order
        task_id_order = {t.task_id: i for i, t in enumerate(tasks)}
        completed_tasks.sort(key=lambda t: task_id_order.get(t.task_id, 0))

        averages = self.calculate_averages(completed_tasks)

        return SchedulerResult(
            algorithm=self.algorithm_name,
            tasks=completed_tasks,
            gantt_chart=gantt_chart,
            total_burst_time=total_burst,
            avg_waiting_time=averages["avg_waiting_time"],
            avg_turnaround_time=averages["avg_turnaround_time"],
            context_switches=context_switches,
            completion_time=current_time,
            preemptive=True
        )
