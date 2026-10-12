"""Experiment and Benchmark Service.

Orchestrates multi-scenario traffic simulation evaluations, runs algorithmic
comparisons, and records benchmark metrics in MySQL for academic analysis.
"""

from typing import Dict, List, Any, Optional

from services.simulation_service import SimulationService
from services.scheduler_service import SchedulerService
from database.repositories import PerformanceRepository

class ExperimentService:
    """Coordinates automated experiments and comparative benchmarking."""

    def __init__(
        self,
        simulation_service: Optional[SimulationService] = None,
        scheduler_service: Optional[SchedulerService] = None,
        perf_repo: Optional[PerformanceRepository] = None
    ):
        self.sim_service = simulation_service or SimulationService()
        self.sched_service = scheduler_service or SchedulerService()
        self.perf_repo = perf_repo or PerformanceRepository()

    def run_traffic_scenario_benchmark(self, duration: int = 45) -> List[Dict[str, Any]]:
        """Run simulation across Low, Medium, and High traffic scenarios and compare metrics."""
        scenarios = ["Low Demand", "Medium Demand", "High Demand"]
        benchmark_results = []

        for sc in scenarios:
            result = self.sim_service.execute_and_persist(
                scenario=sc,
                duration=duration,
                use_gui=False
            )
            run_id = result.get("run_id")
            summary = result.get("summary", {})
            snapshots = result.get("snapshots", [])

            last_speed = snapshots[-1].get("avg_speed_kmh", 0.0) if snapshots else 0.0
            throughput = snapshots[-1].get("throughput_per_min", 0.0) if snapshots else 0.0
            max_queue = max(
                [
                    max(s.get("north_queue", 0), s.get("south_queue", 0), s.get("east_queue", 0), s.get("west_queue", 0))
                    for s in snapshots
                ]
            ) if snapshots else 0

            item = {
                "scenario": sc,
                "run_id": run_id,
                "duration": duration,
                "vehicles_generated": summary.get("total_generated", 0),
                "vehicles_completed": summary.get("total_completed", 0),
                "avg_travel_time": summary.get("avg_travel_time", 0.0),
                "avg_waiting_time": summary.get("avg_waiting_time", 0.0),
                "avg_speed_kmh": last_speed,
                "throughput_per_min": throughput,
                "max_approach_queue": max_queue
            }
            benchmark_results.append(item)

            # Persist to performance_results in MySQL
            try:
                self.perf_repo.insert_performance_metric(
                    scenario_name=sc,
                    algorithm_name="N/A",
                    metric_name="Avg Waiting Time",
                    metric_value=float(summary.get("avg_waiting_time", 0.0)),
                    unit="seconds",
                    simulation_run_id=run_id
                )
                self.perf_repo.insert_performance_metric(
                    scenario_name=sc,
                    algorithm_name="N/A",
                    metric_name="Throughput",
                    metric_value=float(throughput),
                    unit="veh/min",
                    simulation_run_id=run_id
                )
            except Exception:
                pass

        return benchmark_results

    def run_scheduler_benchmark(self, time_quantum: int = 2) -> Dict[str, Any]:
        """Run FCFS, Priority, and Round Robin on the benchmark task set and save metrics."""
        tasks = self.sched_service.generate_traffic_event_tasks()
        results = self.sched_service.compare_all(tasks, time_quantum=time_quantum, persist_to_db=True)

        summary_table = []
        for algo_name, res in results.items():
            row = {
                "algorithm": algo_name,
                "task_count": len(res.tasks),
                "total_burst_time": res.total_burst_time,
                "avg_waiting_time": res.avg_waiting_time,
                "avg_turnaround_time": res.avg_turnaround_time,
                "context_switches": res.context_switches,
                "completion_time": res.completion_time
            }
            summary_table.append(row)

            try:
                self.perf_repo.insert_performance_metric(
                    scenario_name="Traffic Workload",
                    algorithm_name=algo_name,
                    metric_name="Avg Waiting Time",
                    metric_value=float(res.avg_waiting_time),
                    unit="ticks"
                )
                self.perf_repo.insert_performance_metric(
                    scenario_name="Traffic Workload",
                    algorithm_name=algo_name,
                    metric_name="Avg Turnaround Time",
                    metric_value=float(res.avg_turnaround_time),
                    unit="ticks"
                )
            except Exception:
                pass

        return {
            "summary_table": summary_table,
            "detailed_results": results
        }
