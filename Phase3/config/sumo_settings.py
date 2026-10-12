"""SUMO Scenario and Junction Configuration.

Encapsulates junction geometry, approach definitions, signal phase timings,
and vehicle type specifications. Designed so additional junctions or phase plans
can be added without altering application or database logic.
"""

from typing import Dict, List, Any

# Primary junction identifier
JUNCTION_ID = "J0"

# Inbound approach edges entering the junction
INBOUND_EDGES = {
    "North": "N2J0",
    "South": "S2J0",
    "East": "E2J0",
    "West": "W2J0"
}

# Outbound departure edges exiting the junction
OUTBOUND_EDGES = {
    "North": "J02N",
    "South": "J02S",
    "East": "J02E",
    "West": "J02W"
}

# Edge name to human-readable label
EDGE_LABELS = {
    "N2J0": "North Approach (Inbound)",
    "S2J0": "South Approach (Inbound)",
    "E2J0": "East Approach (Inbound)",
    "W2J0": "West Approach (Inbound)",
    "J02N": "North Departure (Outbound)",
    "J02S": "South Departure (Outbound)",
    "J02E": "East Departure (Outbound)",
    "J02W": "West Departure (Outbound)"
}

# Available origin-destination route paths through the 4-arm junction
# Vehicles move through straight, left, or right turns without U-turns.
ROUTE_PATHS = {
    # From North
    "route_N_S": ["N2J0", "J02S"],  # Straight
    "route_N_E": ["N2J0", "J02E"],  # Left
    "route_N_W": ["N2J0", "J02W"],  # Right
    # From South
    "route_S_N": ["S2J0", "J02N"],  # Straight
    "route_S_E": ["S2J0", "J02E"],  # Right
    "route_S_W": ["S2J0", "J02W"],  # Left
    # From East
    "route_E_W": ["E2J0", "J02W"],  # Straight
    "route_E_N": ["E2J0", "J02N"],  # Right
    "route_E_S": ["E2J0", "J02S"],  # Left
    # From West
    "route_W_E": ["W2J0", "J02E"],  # Straight
    "route_W_N": ["W2J0", "J02N"],  # Left
    "route_W_S": ["W2J0", "J02S"]   # Right
}

# Vehicle classes and simulation physical parameters
VEHICLE_TYPES: Dict[str, Dict[str, Any]] = {
    "passenger": {
        "accel": "2.6",
        "decel": "4.5",
        "length": "5.0",
        "minGap": "2.5",
        "maxSpeed": "14.0",  # ~50 km/h
        "color": "0.2,0.6,1.0",  # Blue
        "vClass": "passenger",
        "weight": 0.70  # 70% of traffic
    },
    "bus": {
        "accel": "1.2",
        "decel": "3.5",
        "length": "12.0",
        "minGap": "3.0",
        "maxSpeed": "11.0",  # ~40 km/h
        "color": "1.0,0.8,0.0",  # Yellow/Gold
        "vClass": "bus",
        "weight": 0.15  # 15% of traffic
    },
    "delivery": {
        "accel": "1.8",
        "decel": "4.0",
        "length": "7.5",
        "minGap": "2.5",
        "maxSpeed": "12.5",  # ~45 km/h
        "color": "0.3,0.8,0.3",  # Green
        "vClass": "delivery",
        "weight": 0.10  # 10% of traffic
    },
    "emergency": {
        "accel": "3.5",
        "decel": "5.0",
        "length": "6.0",
        "minGap": "2.0",
        "maxSpeed": "20.0",  # ~72 km/h
        "color": "1.0,0.1,0.1",  # Red
        "vClass": "emergency",
        "weight": 0.05  # 5% of traffic
    }
}

# Safe Conflict-Free Signal Program for 4-Arm Junction J0
# Each phase index corresponds to a distinct signal state.
# Total Cycle Time: 30 + 4 + 2 + 30 + 4 + 2 = 72 seconds
SIGNAL_PHASES = [
    {
        "index": 0,
        "name": "North-South Green",
        "description": "North and South inbound traffic have Green. East-West traffic has Red.",
        "duration": 30,
        "state_str": "GGGgrrrrGGGgrrrr",  # NS straight and right green
        "active_corridor": "North-South"
    },
    {
        "index": 1,
        "name": "North-South Yellow",
        "description": "North and South inbound traffic transition to Yellow.",
        "duration": 4,
        "state_str": "yyyyrrrryyyyrrrr",
        "active_corridor": "North-South"
    },
    {
        "index": 2,
        "name": "All-Red Clearance (NS -> EW)",
        "description": "All approaches have Red to clear the intersection box safely.",
        "duration": 2,
        "state_str": "rrrrrrrrrrrrrrrr",
        "active_corridor": "None (Clearance)"
    },
    {
        "index": 3,
        "name": "East-West Green",
        "description": "East and West inbound traffic have Green. North-South traffic has Red.",
        "duration": 30,
        "state_str": "rrrrGGGgrrrrGGGg",  # EW straight and right green
        "active_corridor": "East-West"
    },
    {
        "index": 4,
        "name": "East-West Yellow",
        "description": "East and West inbound traffic transition to Yellow.",
        "duration": 4,
        "state_str": "rrrryyyyrrrryyyy",
        "active_corridor": "East-West"
    },
    {
        "index": 5,
        "name": "All-Red Clearance (EW -> NS)",
        "description": "All approaches have Red to clear intersection box safely.",
        "duration": 2,
        "state_str": "rrrrrrrrrrrrrrrr",
        "active_corridor": "None (Clearance)"
    }
]
