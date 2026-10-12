"""SUMO Simulation Lifecycle Manager.

Coordinates configuration loading, binary discovery, subprocess startup,
TraCI connection lifecycle, signal control, metrics tracking, and stepping.
Supports both fast headless execution and smooth, visible GUI simulation.
"""

import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

from config.settings import (
    SUMO_FILES_DIR,
    DEFAULT_STEP_LENGTH,
    get_sumo_binary,
    check_sumo_available
)
from simulation.traci_client import TraCIClient
from simulation.signal_controller import SignalController
from simulation.traffic_metrics import TrafficMetricsTracker
from simulation.traffic_generator import TrafficGenerator

class SimulationState:
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    FINISHED = "FINISHED"


class SumoManager:
    """Manages the full lifecycle of a SUMO simulation run."""

    def __init__(self, sumo_files_dir: Optional[Path] = None):
        self.sumo_files_dir = sumo_files_dir or SUMO_FILES_DIR
        self.config_file = self.sumo_files_dir / "simulation.sumocfg"
        
        self.client = TraCIClient()
        self.signal_controller = SignalController()
        self.metrics_tracker = TrafficMetricsTracker()
        self.traffic_generator = TrafficGenerator(self.sumo_files_dir)
        
        self.state = SimulationState.IDLE
        self.current_time = 0.0
        self.max_duration = 120
        self.step_length = DEFAULT_STEP_LENGTH
        self.run_id: Optional[int] = None
        self.active_scenario = "Medium Demand"

        # GUI visual settings
        self.use_gui = False
        self.gui_delay_ms = 100
        self.quit_on_end = False

    def is_available(self) -> bool:
        """Check if SUMO binary is available on the host system."""
        return check_sumo_available()

    def launch_standalone_gui(self, delay_ms: int = 100) -> subprocess.Popen:
        """Launch SUMO GUI as an interactive standalone window for desktop observation."""
        gui_bin = get_sumo_binary(use_gui=True)
        cmd = [
            gui_bin,
            "-c", str(self.config_file),
            "--delay", str(delay_ms)
        ]
        return subprocess.Popen(cmd)

    def start_simulation(
        self,
        scenario: str = "Medium Demand",
        duration: int = 120,
        use_gui: bool = False,
        vehicle_count: Optional[int] = None,
        seed: int = 42,
        gui_delay_ms: int = 100,
        quit_on_end: bool = False
    ) -> bool:
        """Prepare traffic demand and start SUMO process with TraCI connection."""
        if self.state in (SimulationState.RUNNING, SimulationState.PAUSED):
            self.stop_simulation()

        # Generate traffic demand for the requested scenario
        self.traffic_generator.generate_demand(
            scenario_name=scenario,
            duration=duration,
            vehicle_count=vehicle_count,
            seed=seed
        )

        self.active_scenario = scenario
        self.max_duration = duration
        self.current_time = 0.0
        self.use_gui = use_gui
        self.gui_delay_ms = gui_delay_ms
        self.quit_on_end = quit_on_end

        self.metrics_tracker.reset()
        self.signal_controller = SignalController()

        binary = get_sumo_binary(use_gui=use_gui)
        
        cmd = [
            binary,
            "-c", str(self.config_file),
            "--step-length", str(self.step_length),
            "--begin", "0",
            "--end", str(duration + 10),
            "--no-step-log", "true",
            "--time-to-teleport", "-1"
        ]

        if use_gui:
            cmd.extend([
                "--start", "true",
                "--delay", str(gui_delay_ms),
                "--quit-on-end", "true" if quit_on_end else "false"
            ])

        success = self.client.start(cmd, label="smart_traffic_sim")
        if success:
            self.state = SimulationState.RUNNING
        return success

    def step(self) -> Optional[Dict[str, Any]]:
        """Advance simulation by one time step and collect metrics.
        
        Returns:
            Snapshot dictionary of traffic metrics for the step, or None if finished.
        """
        if self.state not in (SimulationState.RUNNING, SimulationState.PAUSED):
            return None

        if self.current_time >= self.max_duration:
            self.state = SimulationState.FINISHED
            self.stop_simulation()
            return None

        try:
            self.current_time = self.client.simulation_step()

            # If running in GUI mode, pause briefly so human eye can watch cars move
            if self.use_gui and self.gui_delay_ms > 0:
                time.sleep(self.gui_delay_ms / 1000.0)
            
            # Update signal controller logic
            sig_event = self.signal_controller.update_step(
                traci_conn=self.client._traci,
                sim_time=self.current_time,
                step_size=self.step_length
            )

            # Query vehicle state
            active_ids = self.client.get_active_vehicle_ids()
            departed_ids = self.client.get_departed_vehicle_ids()
            arrived_ids = self.client.get_arrived_vehicle_ids()

            veh_data_map = {}
            for v_id in active_ids:
                veh_data_map[v_id] = self.client.get_vehicle_data(v_id)

            curr_phase = self.signal_controller.get_current_phase_info()

            snapshot = self.metrics_tracker.record_step(
                sim_time=self.current_time,
                active_veh_ids=active_ids,
                departed_veh_ids=departed_ids,
                arrived_veh_ids=arrived_ids,
                veh_data_map=veh_data_map,
                phase_index=curr_phase["index"],
                phase_name=curr_phase["name"],
                corridor=curr_phase["active_corridor"]
            )

            # Check if simulation exceeded max duration
            if self.current_time >= self.max_duration:
                self.state = SimulationState.FINISHED
                self.client.close()

            return snapshot

        except Exception as e:
            self.state = SimulationState.STOPPED
            self.client.close()
            raise RuntimeError(f"Simulation step error: {e}") from e

    def pause_simulation(self) -> None:
        """Pause running simulation."""
        if self.state == SimulationState.RUNNING:
            self.state = SimulationState.PAUSED

    def resume_simulation(self) -> None:
        """Resume paused simulation."""
        if self.state == SimulationState.PAUSED:
            self.state = SimulationState.RUNNING

    def stop_simulation(self) -> None:
        """Stop and close simulation cleanly."""
        self.client.close()
        if self.state != SimulationState.FINISHED:
            self.state = SimulationState.STOPPED

    def run_complete(
        self,
        scenario: str = "Medium Demand",
        duration: int = 60,
        use_gui: bool = False,
        vehicle_count: Optional[int] = None,
        seed: int = 42,
        gui_delay_ms: int = 100,
        quit_on_end: bool = False
    ) -> List[Dict[str, Any]]:
        """Execute a full simulation run and return all step snapshots."""
        self.start_simulation(
            scenario=scenario,
            duration=duration,
            use_gui=use_gui,
            vehicle_count=vehicle_count,
            seed=seed,
            gui_delay_ms=gui_delay_ms,
            quit_on_end=quit_on_end
        )

        snapshots = []
        while self.state == SimulationState.RUNNING:
            snap = self.step()
            if snap:
                snapshots.append(snap)
            else:
                break

        self.stop_simulation()
        return snapshots
