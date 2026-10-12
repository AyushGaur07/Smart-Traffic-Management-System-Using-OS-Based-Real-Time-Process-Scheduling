"""Application settings and environment variable management.

This module centrally manages database parameters, paths, and simulation
execution defaults, reading overrides from the local .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SUMO_FILES_DIR = PROJECT_ROOT / "sumo_files"
DATABASE_DIR = PROJECT_ROOT / "database"

# Load local .env
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_FILE)

# MySQL Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "smart_traffic_db")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

# Simulation execution settings
DEFAULT_GUI_ENABLED = os.getenv("SUMO_GUI", "false").strip().lower() in ("true", "1", "yes")
DEFAULT_STEP_LENGTH = float(os.getenv("SUMO_STEP_LENGTH", "1.0"))
DEFAULT_SIMULATION_DURATION = 120  # seconds

# Traffic demand scenarios
TRAFFIC_SCENARIOS = {
    "Low Demand": {
        "vehicle_count": 30,
        "insertion_interval": 4.0,  # 1 vehicle every ~4 seconds
        "description": "Light, free-flowing traffic. Minimal queueing at the junction."
    },
    "Medium Demand": {
        "vehicle_count": 75,
        "insertion_interval": 1.6,  # 1 vehicle every ~1.6 seconds
        "description": "Moderate suburban density. Moderate cyclic queues during red lights."
    },
    "High Demand": {
        "vehicle_count": 160,
        "insertion_interval": 0.75,  # 1 vehicle every ~0.75 seconds
        "description": "Peak rush-hour congestion with heavy multi-approach queues."
    }
}

# Scheduling configuration constants
TIME_QUANTUM_DEFAULT = 2  # Round Robin time slice in simulation/virtual ticks

def get_sumo_binary(use_gui: bool = False) -> str:
    """Detect and return the absolute path to the SUMO binary.
    
    Checks sumolib first (handles eclipse-sumo pip install and SUMO_HOME),
    then checks standard PATH or environment overrides.
    """
    binary_name = "sumo-gui" if use_gui else "sumo"
    try:
        import sumolib
        return sumolib.checkBinary(binary_name)
    except Exception:
        # Fallback to plain binary name in system PATH
        return f"{binary_name}.exe" if os.name == "nt" else binary_name

def check_sumo_available() -> bool:
    """Return True if SUMO executable can be located and run."""
    try:
        binary = get_sumo_binary(use_gui=False)
        return os.path.exists(binary) or bool(os.popen(f"{binary} --version").read())
    except Exception:
        return False
