"""Traffic Demand Generator.

Generates reproducible, parameterized SUMO route files (.rou.xml) for low,
medium, and high traffic-demand scenarios. Provides complete transparency into
how every vehicle departure, route, and type is determined.
"""

import os
import random
from pathlib import Path
from typing import Dict, List, Any, Optional

from config.settings import SUMO_FILES_DIR, TRAFFIC_SCENARIOS
from config.sumo_settings import ROUTE_PATHS, VEHICLE_TYPES

class TrafficGenerator:
    """Generates SUMO route files with configurable traffic demand."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or SUMO_FILES_DIR
        self.route_keys = list(ROUTE_PATHS.keys())
        self.vtype_keys = list(VEHICLE_TYPES.keys())
        self.vtype_weights = [VEHICLE_TYPES[k]["weight"] for k in self.vtype_keys]

    def generate_demand(
        self,
        scenario_name: str = "Medium Demand",
        duration: int = 120,
        vehicle_count: Optional[int] = None,
        seed: int = 42,
        output_filename: str = "routes.rou.xml"
    ) -> Dict[str, Any]:
        """Generate a complete .rou.xml file for the given scenario.
        
        Returns:
            Dictionary containing metadata, file path, and list of generated vehicles.
        """
        random.seed(seed)
        scenario_cfg = TRAFFIC_SCENARIOS.get(scenario_name, TRAFFIC_SCENARIOS["Medium Demand"])
        total_vehicles = vehicle_count if vehicle_count is not None else scenario_cfg["vehicle_count"]

        # Calculate departure times evenly or with slight stochastic jitter
        # Ensuring all departures fit within simulation duration
        departures: List[Dict[str, Any]] = []
        if total_vehicles > 0:
            avg_interval = duration / total_vehicles
            current_time = 1.0

            for i in range(total_vehicles):
                # Add slight random jitter (+/- 25% of interval)
                jitter = random.uniform(-0.25 * avg_interval, 0.25 * avg_interval)
                depart_time = max(0.5, round(current_time + jitter, 1))
                if depart_time >= duration:
                    depart_time = duration - 1.0

                # Sample vehicle type based on realistic traffic distribution
                vtype = random.choices(self.vtype_keys, weights=self.vtype_weights, k=1)[0]
                
                # Sample route uniformly across the 12 OD pairs
                route_id = random.choice(self.route_keys)
                
                veh_info = {
                    "id": f"veh_{scenario_name.lower().replace(' ', '_')}_{i:03d}",
                    "type": vtype,
                    "route": route_id,
                    "depart": depart_time,
                    "departLane": "best",
                    "departSpeed": "max"
                }
                departures.append(veh_info)
                current_time += avg_interval

        # Sort strictly by departure time
        departures.sort(key=lambda v: v["depart"])

        # Write to XML file
        target_path = self.output_dir / output_filename
        self._write_routes_xml(target_path, departures)

        return {
            "file_path": str(target_path),
            "scenario": scenario_name,
            "duration": duration,
            "seed": seed,
            "vehicle_count": len(departures),
            "vehicles": departures,
            "description": scenario_cfg.get("description", "")
        }

    def _write_routes_xml(self, file_path: Path, departures: List[Dict[str, Any]]) -> None:
        """Write the XML routes document."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">',
            '    <!-- Route Definitions for 4-Arm Junction J0 -->'
        ]

        # Add route paths
        for r_id, edges in ROUTE_PATHS.items():
            edge_str = " ".join(edges)
            lines.append(f'    <route id="{r_id}" edges="{edge_str}"/>')

        lines.append('')
        lines.append('    <!-- Generated Vehicle Schedule -->')
        for v in departures:
            lines.append(
                f'    <vehicle id="{v["id"]}" type="{v["type"]}" '
                f'route="{v["route"]}" depart="{v["depart"]:.1f}" '
                f'departLane="{v["departLane"]}" departSpeed="{v["departSpeed"]}"/>'
            )

        lines.append('</routes>')

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
