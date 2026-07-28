# ME325 — Decentralised HVAC Control Implementation Details

This document provides a comprehensive and thorough breakdown of all components, scripts, and algorithms implemented in the ME325 Decentralised HVAC Control project. The system simulates a 5-zone commercial office building in **EnergyPlus**, with control co-executed in **Python** using a decentralised architecture.

---

## 1. System Architecture & Core Execution

The project relies on a co-simulation architecture where EnergyPlus handles the building physics, and Python handles the control logic.

### 1.1 `main.py` (The Orchestrator)
- **Role:** Serves as the primary entry point and co-simulation driver.
- **Implementation Details:**
  - Uses the `pyenergyplus` API to hook into the EnergyPlus simulation loop.
  - Registers a callback (`callback_end_zone_timestep_after_zone_reporting`) that fires after every zone reporting timestep.
  - Resolves EnergyPlus handles for:
    - Actuators: `sat_sp` (System Node Setpoint), `oa_flow` (Outdoor Air Controller), `mdot` (AirTerminal), `csp` (Zone Temp Control).
    - Variables: `T` (Zone Mean Air Temp), `w` (Humidity Ratio), `rh` (Relative Humidity), `co2` (CO₂ Concentration).
  - Drives the timestep loop: Reads sensor data, invokes zone controllers, invokes the AHU coordinator, writes actuator commands back to EnergyPlus, and logs data to `out/control_log.csv`.

### 1.2 `config.py` (System Configuration)
- **Role:** Defines system-wide constants and zone-specific parameters.
- **Implementation Details:**
  - Stores global settings like `CO2_SETPOINT` (800 ppm), `OUTDOOR_CO2` (400 ppm), `SAT_FLOOR` (10°C).
  - Holds configuration for all 5 zones (Zone 1 through 5), specifying their use cases, maximum flows, PI gains (`Kp`, `Ki`), temperature setpoints, and relative humidity targets.

---

## 2. Control Philosophy

The control architecture is split into a hierarchical two-level system: decentralised zone-level PI controllers and a central AHU coordinator.

### 2.1 Zone-Level Control (`controllers/`)
- **`zone_controller.py` (Base Class):**
  - Implements an independent PI control loop for each zone.
  - Drives the supply air mass flow rate (`mdot`) to maintain the zone temperature setpoint.
  - **Anti-Windup Mechanism:** Uses a conditional integration (clamping) method. The integrator update is only applied if the output is not saturated, preventing severe overshoots.
  - **Humidity Override:** If relative humidity exceeds the target, it requests a colder supply air temperature (12°C instead of 14°C) for dehumidification.
- **Zone Implementations (`zone1.py`, `zone2.py`, `zone3.py`, `zone5.py`):**
  - Standard implementations inheriting from the base controller, applied to Open Office, Private Offices, Conference Room, and Reception.
- **Server Room Override (`zone4.py`):**
  - Overrides the base logic to enforce a strict minimum airflow floor (30% of max capacity) ensuring the Server Room never completely loses cooling or airflow.

### 2.2 AHU Coordinator (`controllers/ahu.py`)
- **Role:** Resolves system-wide conflicts from the decentralised requests.
- **Implementation Details:**
  - **Supply Air Temperature (SAT):** Serves the most demanding zone by taking the minimum requested SAT across all zones (clamped to a 10°C floor).
  - **Outdoor Air (OA) Flow:** Implements a Demand-Controlled Ventilation (DCV) strategy. OA flow is scaled proportionally based on the zone with the worst (highest) CO₂ concentration, clamped between 15% (code minimum) and 100%.

---

## 3. State Estimation

### 3.1 Extended Kalman Filter (`estimation/ekf.py`)
- **Role:** Designed to filter noisy sensor readings and estimate hidden physical parameters for each zone.
- **Implementation Details:**
  - **Augmented State Vector:** Contains observable states (`T`, `w`, `c`) and hidden parameters (`C_T` thermal capacitance, `U` heat transfer, `C_w` moisture capacitance, `k` CO₂ generation, `q_occ` occupancy heat gain).
  - **Physical Sub-Models:** Formulated with thermal balance, moisture balance, and CO₂ mass balance equations.
  - **Random Walk Dynamics:** Hidden parameters are modelled to vary slowly via a random walk, allowing tracking of unmeasured disturbances like occupancy changes.
  - *(Note: Currently scaffolded; falls back gracefully to standard PI control if physics Jacobians are not fully integrated).*

### 3.2 Occupancy Mirror (`occupancy.py`)
- **Role:** Replicates the EnergyPlus 'Office Occupancy' schedule for logging purposes without affecting actual simulation actuators.
- **Implementation Details:**
  - Mirrors the `Schedule:Compact` defined in the IDF file for weekdays and weekends.
  - Maps fractions to absolute people counts based on the peak occupancy specified for each zone (e.g., 12 for the Conference Room, 1 for the Server Room).

---

## 4. Building Physics & Models

### 4.1 EnergyPlus Models (`model/`)
- **`MultiZone_VAV_PythonControl.idf`:** The primary 5-zone commercial office building model.
- **`1Zone_SriLanka_Controlled.idf`:** A single-zone prototype used for reference/legacy testing.
- **`Colombo.epw`:** Weather file for Colombo, Sri Lanka (Hot-humid tropical). Chosen specifically because it requires year-round cooling and heavy dehumidification.

---

## 5. Output Logging, Analysis, and Visualization

The project includes multiple robust mechanisms for monitoring and analyzing the co-simulation results.

### 5.1 Terminal Analysis (`analyse_results.py`)
- **Role:** Generates a statistical performance report from the `control_log.csv`.
- **Implementation Details:**
  - Processes temperature comfort (mean, std, ±1°C/2°C bands, setpoint violations).
  - Analyzes air quality (CO₂ limits vs ASHRAE 1000ppm standard).
  - Evaluates humidity levels and airflow utilization percentages.

### 5.2 Python Data Visualization (`visualize.py`)
- **Role:** Plots static, interactive matplotlib graphs.
- **Implementation Details:**
  - Generates three dark-themed figures: Temperature tracking, Relative Humidity, and CO₂ levels.
  - Uses customized zone colors and rolling 24-hour mean overlays for trend analysis.

### 5.3 Live Web Dashboard (`dashboard.html`)
- **Role:** Provides a premium, interactive "playback" dashboard for the simulation log.
- **Implementation Details:**
  - **Glassmorphism UI:** Built with modern CSS featuring translucent panels, blur filters, and a responsive grid.
  - **File Handling:** Includes a drag-and-drop zone and an auto-load feature for `control_log.csv`.
  - **Interactive Playback:** Features a transport bar to play, pause, step forward, and adjust playback speed (1x to 500x).
  - **Live KPI Tracking:** Zone cards with real-time indicators for Temp, Humidity, CO₂, and Airflow, with pulsing status dots (OK, WARNING, CRITICAL).
  - **AHU Gauges:** Visual gauges indicating SAT setpoint, Outdoor Air mass flow, OA ratio, and Worst-Zone CO₂.
  - **Dynamic Charts:** Powered by `Chart.js`, plotting historical rolling data for all metrics, with interactive dropdowns to filter specific zones.

---

## 6. Execution Workflow

1. **Virtual Environment Setup:** Uses `requirements.txt` (`pandas`, `matplotlib`, `numpy`).
2. **Simulation Run:** `python main.py` triggers the EnergyPlus engine and Python API loop, producing `out/control_log.csv`.
3. **Review:** Data is visualized either via the terminal (`analyse_results.py`), the matplotlib script (`visualize.py`), or the interactive web UI (`dashboard.html`).
