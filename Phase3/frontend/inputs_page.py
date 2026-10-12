"""Inputs and Traffic Generation Page.

Provides complete transparency into SUMO scenario files, route definitions,
departure generation mathematics, vehicle classes, and the path from input
files to TraCI observations and MySQL records.
"""

import os
import streamlit as st
import pandas as pd
from pathlib import Path

from config.settings import SUMO_FILES_DIR, TRAFFIC_SCENARIOS
from config.sumo_settings import (
    JUNCTION_ID,
    INBOUND_EDGES,
    OUTBOUND_EDGES,
    ROUTE_PATHS,
    VEHICLE_TYPES,
    SIGNAL_PHASES
)
from simulation.traffic_generator import TrafficGenerator

def render_inputs_page():
    st.title("📋 Inputs and Traffic Generation")
    st.markdown(
        "A student must be able to explain where every simulation input originates. "
        "This page exposes the configuration files, route generation algorithms, vehicle parameters, "
        "and data transition pipeline."
    )

    # 1. Pipeline Distinction Guide
    st.subheader("🔄 Data Transition Pipeline: 4 Distinct Stages")
    st.info(
        "**1. Configured Inputs**: Static network geometry, physical vehicle classes, and XML configuration files.\n\n"
        "**2. Generated Traffic Demand**: Programmatically generated vehicle departure schedules (`.rou.xml`) based on scenario rates.\n\n"
        "**3. Live SUMO Observations**: Real-time vehicle positions, approach queue lengths, and speeds polled via TraCI sockets.\n\n"
        "**4. Persisted Database Records**: Parameterized transactional inserts into MySQL tables (`simulation_runs`, `traffic_snapshots`, etc.)."
    )

    st.divider()

    # 2. File Location Inspector
    st.subheader("📁 SUMO Input Files & Locations")
    files_info = [
        ("Configuration (.sumocfg)", SUMO_FILES_DIR / "simulation.sumocfg", "Ties network, routes, and additional files together."),
        ("Network (.net.xml)", SUMO_FILES_DIR / "network.net.xml", "Junction J0 topology, lane geometry, turn connections, and signal logic."),
        ("Routes (.rou.xml)", SUMO_FILES_DIR / "routes.rou.xml", "Route paths through J0 and departure schedules."),
        ("Vehicle Types (.add.xml)", SUMO_FILES_DIR / "vehicle_types.add.xml", "Physical vehicle specifications (length, acceleration, color)."),
        ("Nodes Definition (.nod.xml)", SUMO_FILES_DIR / "nodes.nod.xml", "J0 coordinate (0,0) and outer anchor nodes (250m)."),
        ("Edges Definition (.edg.xml)", SUMO_FILES_DIR / "edges.edg.xml", "Two-lane approach and departure road definitions.")
    ]

    df_files = pd.DataFrame([
        {
            "File Type": f[0],
            "Absolute File Path": str(f[1]),
            "Exists": "✅ Yes" if f[1].exists() else "❌ Missing",
            "Description": f[2]
        }
        for f in files_info
    ])
    st.dataframe(df_files, use_container_width=True)

    # XML Viewer Tabs
    st.subheader("📜 Inspect Raw XML Input Files")
    tab_cfg, tab_net, tab_rou, tab_vtype = st.tabs([
        "simulation.sumocfg", "network.net.xml (excerpt)", "routes.rou.xml", "vehicle_types.add.xml"
    ])

    with tab_cfg:
        cfg_path = SUMO_FILES_DIR / "simulation.sumocfg"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                st.code(f.read(), language="xml")

    with tab_net:
        net_path = SUMO_FILES_DIR / "network.net.xml"
        if net_path.exists():
            with open(net_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                st.code("".join(lines[:120]), language="xml")
                st.caption(f"Showing first 120 lines of {len(lines)} total network XML lines.")

    with tab_rou:
        rou_path = SUMO_FILES_DIR / "routes.rou.xml"
        if rou_path.exists():
            with open(rou_path, "r", encoding="utf-8") as f:
                st.code(f.read(), language="xml")

    with tab_vtype:
        vtype_path = SUMO_FILES_DIR / "vehicle_types.add.xml"
        if vtype_path.exists():
            with open(vtype_path, "r", encoding="utf-8") as f:
                st.code(f.read(), language="xml")

    st.divider()

    # 3. Vehicle Classes & Route Paths
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("🚗 Vehicle Class Physical Parameters")
        vtypes_data = []
        for k, v in VEHICLE_TYPES.items():
            vtypes_data.append({
                "Vehicle Class": k,
                "Length (m)": v["length"],
                "Max Speed (m/s)": v["maxSpeed"],
                "Speed (km/h)": round(float(v["maxSpeed"]) * 3.6, 1),
                "Accel (m/s²)": v["accel"],
                "Decel (m/s²)": v["decel"],
                "Traffic Share": f"{int(v['weight'] * 100)}%"
            })
        st.dataframe(pd.DataFrame(vtypes_data), use_container_width=True)

    with col_right:
        st.subheader("🛣️ Junction J0 Origin-Destination Routes")
        routes_data = [
            {"Route ID": rid, "Inbound Approach": edges[0], "Outbound Departure": edges[1]}
            for rid, edges in ROUTE_PATHS.items()
        ]
        st.dataframe(pd.DataFrame(routes_data), use_container_width=True)

    st.divider()

    # 4. Interactive Traffic Demand Generator
    st.subheader("🎲 Interactive Traffic Demand Generator Preview")
    st.markdown(
        "Experiment with demand generation parameters to see exactly how departure times, "
        "vehicle classes, and routes are computed prior to running SUMO."
    )

    gen_col1, gen_col2, gen_col3 = st.columns(3)
    with gen_col1:
        sel_scenario = st.selectbox("Preset Scenario", list(TRAFFIC_SCENARIOS.keys()), index=1)
    with gen_col2:
        custom_vehicles = st.number_input("Total Vehicle Count", min_value=5, max_value=250, value=TRAFFIC_SCENARIOS[sel_scenario]["vehicle_count"])
    with gen_col3:
        custom_duration = st.number_input("Duration (seconds)", min_value=20, max_value=300, value=60)

    generator = TrafficGenerator()
    generated_result = generator.generate_demand(
        scenario_name=sel_scenario,
        duration=custom_duration,
        vehicle_count=custom_vehicles,
        seed=42,
        output_filename="routes.rou.xml"
    )

    st.write(f"Generated **{len(generated_result['vehicles'])} vehicles** scheduled over **{custom_duration} seconds**:")
    df_preview = pd.DataFrame(generated_result["vehicles"])
    st.dataframe(df_preview, use_container_width=True)
