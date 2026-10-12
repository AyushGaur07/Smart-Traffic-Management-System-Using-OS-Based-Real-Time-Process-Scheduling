"""Unit tests for OS CPU Scheduling algorithms.

Validates FCFS, Priority (non-preemptive & preemptive), and Round Robin
scheduling behavior, tie-breaking, queue rotation, context switches,
and mathematical correctness of turnaround and waiting times.
"""

import pytest
from scheduler.task_model import Task, TaskStatus
from scheduler.fcfs import FCFSScheduler
from scheduler.priority import PriorityScheduler
from scheduler.round_robin import RoundRobinScheduler

def test_fcfs_execution_order_and_times():
    """Verify FCFS executes strictly in arrival order and correctly computes metrics."""
    tasks = [
        Task("T1", "Task 1", "test", "event", arrival_time=0, burst_time=5, priority=3),
        Task("T2", "Task 2", "test", "event", arrival_time=2, burst_time=3, priority=1),
        Task("T3", "Task 3", "test", "event", arrival_time=4, burst_time=2, priority=2),
    ]

    scheduler = FCFSScheduler()
    result = scheduler.schedule(tasks)

    # Execution order must be T1 -> T2 -> T3
    order = [t.task_id for t in result.tasks]
    assert order == ["T1", "T2", "T3"]

    # T1: arrives 0, starts 0, completes 5. TAT=5, Wait=0
    t1 = next(t for t in result.tasks if t.task_id == "T1")
    assert t1.start_time == 0
    assert t1.completion_time == 5
    assert t1.turnaround_time == 5
    assert t1.waiting_time == 0
    assert t1.status == TaskStatus.COMPLETED

    # T2: arrives 2, starts 5, completes 8. TAT=8-2=6, Wait=6-3=3
    t2 = next(t for t in result.tasks if t.task_id == "T2")
    assert t2.start_time == 5
    assert t2.completion_time == 8
    assert t2.turnaround_time == 6
    assert t2.waiting_time == 3

    # T3: arrives 4, starts 8, completes 10. TAT=10-4=6, Wait=6-2=4
    t3 = next(t for t in result.tasks if t.task_id == "T3")
    assert t3.start_time == 8
    assert t3.completion_time == 10
    assert t3.turnaround_time == 6
    assert t3.waiting_time == 4

    # Averages: Avg Wait = (0+3+4)/3 = 2.33, Avg TAT = (5+6+6)/3 = 5.67
    assert result.avg_waiting_time == pytest.approx(2.33, 0.01)
    assert result.avg_turnaround_time == pytest.approx(5.67, 0.01)
    assert result.context_switches == 2


def test_fcfs_cpu_idle_gap():
    """Verify FCFS handles idle CPU intervals when next task arrives in the future."""
    tasks = [
        Task("T1", "Task 1", "test", "event", arrival_time=0, burst_time=2, priority=1),
        Task("T2", "Task 2", "test", "event", arrival_time=5, burst_time=3, priority=1),
    ]
    scheduler = FCFSScheduler()
    result = scheduler.schedule(tasks)

    t1 = next(t for t in result.tasks if t.task_id == "T1")
    t2 = next(t for t in result.tasks if t.task_id == "T2")

    assert t1.completion_time == 2
    assert t2.start_time == 5
    assert t2.completion_time == 8
    assert t2.waiting_time == 0  # No queue delay, CPU was waiting for it


def test_priority_non_preemptive():
    """Verify Non-Preemptive Priority selects highest priority among ready tasks."""
    # Priority convention: Lower numeric value = higher priority
    tasks = [
        Task("T1", "Low Priority Initial", "test", "event", arrival_time=0, burst_time=4, priority=4),
        Task("T2", "Medium Priority", "test", "event", arrival_time=1, burst_time=3, priority=3),
        Task("T3", "High Priority", "test", "event", arrival_time=2, burst_time=2, priority=1),
    ]

    scheduler = PriorityScheduler(preemptive=False)
    result = scheduler.schedule(tasks)

    # T1 arrives first at 0 and runs non-preemptively until 4.
    # At t=4, both T2 and T3 are ready. T3 has higher priority (1 < 3), so T3 runs next!
    execution_seq = [s.task_id for s in result.gantt_chart]
    assert execution_seq == ["T1", "T3", "T2"]

    t3 = next(t for t in result.tasks if t.task_id == "T3")
    assert t3.start_time == 4
    assert t3.completion_time == 6
    assert t3.waiting_time == 2  # Arrived at 2, waited until 4


def test_priority_preemptive():
    """Verify Preemptive Priority immediately preempts lower-priority tasks."""
    tasks = [
        Task("T1", "Normal Task", "test", "event", arrival_time=0, burst_time=6, priority=3),
        Task("T2", "Urgent Interrupt", "test", "event", arrival_time=2, burst_time=2, priority=1),
    ]

    scheduler = PriorityScheduler(preemptive=True)
    result = scheduler.schedule(tasks)

    # T1 runs from 0 to 2 (duration 2, remaining 4).
    # At t=2, T2 arrives with priority 1 (higher than T1's 3). T2 preempts T1.
    # T2 runs from 2 to 4 and completes.
    # T1 resumes from 4 to 8 and completes.
    gantt_ids = [s.task_id for s in result.gantt_chart]
    assert gantt_ids == ["T1", "T2", "T1"]

    t2 = next(t for t in result.tasks if t.task_id == "T2")
    assert t2.start_time == 2
    assert t2.completion_time == 4
    assert t2.waiting_time == 0

    t1 = next(t for t in result.tasks if t.task_id == "T1")
    assert t1.completion_time == 8
    assert t1.turnaround_time == 8
    assert t1.waiting_time == 2  # Delayed by T2's 2 ticks


def test_round_robin_time_slicing():
    """Verify Round Robin rotates tasks according to time quantum."""
    tasks = [
        Task("T1", "Task 1", "test", "event", arrival_time=0, burst_time=5, priority=1),
        Task("T2", "Task 2", "test", "event", arrival_time=0, burst_time=3, priority=1),
    ]

    scheduler = RoundRobinScheduler(time_quantum=2)
    result = scheduler.schedule(tasks)

    # Quantum = 2:
    # t=0: T1 executes [0, 2], rem=3
    # t=2: T2 executes [2, 4], rem=1
    # t=4: T1 executes [4, 6], rem=1
    # t=6: T2 executes [6, 7], completed!
    # t=7: T1 executes [7, 8], completed!
    gantt_ids = [s.task_id for s in result.gantt_chart]
    assert gantt_ids == ["T1", "T2", "T1", "T2", "T1"]

    t2 = next(t for t in result.tasks if t.task_id == "T2")
    assert t2.completion_time == 7
    assert t2.waiting_time == 4

    t1 = next(t for t in result.tasks if t.task_id == "T1")
    assert t1.completion_time == 8
    assert t1.waiting_time == 3


def test_empty_tasks_handled_gracefully():
    """Ensure all schedulers handle empty task sets without crashing."""
    for s in [FCFSScheduler(), PriorityScheduler(False), PriorityScheduler(True), RoundRobinScheduler(2)]:
        res = s.schedule([])
        assert res.total_burst_time == 0
        assert res.avg_waiting_time == 0.0
        assert len(res.tasks) == 0
