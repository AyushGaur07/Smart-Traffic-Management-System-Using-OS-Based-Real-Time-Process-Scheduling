# Smart Traffic Management System

A college project that simulates a four-way traffic junction with SUMO, Python, MySQL, and Streamlit. It supports fixed-time signals and adaptive control using CPU scheduling algorithms.

## Requirements

- Python
- SUMO (available on `PATH` or configured with `SUMO_HOME`)
- MySQL

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your MySQL credentials.

## Run

```powershell
streamlit run app.py
```

Open the dashboard, initialize the database, then use **Traffic Simulation** to choose fixed or adaptive mode and a scheduling algorithm.

## Main files

- `app.py` — Streamlit dashboard
- `traffic.py` — SUMO/TraCI traffic simulation
- `scheduler.py` — CPU scheduling algorithms
- `database.py` — MySQL storage
- `sumo/` — SUMO network and routes
