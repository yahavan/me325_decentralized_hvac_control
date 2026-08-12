# ME325 — Decentralised HVAC Control (3YP)
### A Multi-Zone VAV System with Python-Driven EnergyPlus Co-simulation

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Building & Zone Configuration](#3-building--zone-configuration)
4. [Control Philosophy — Decentralised + Coordinated](#4-control-philosophy--decentralised--coordinated)
5. [Zone-Level PI Controller](#5-zone-level-pi-controller)
6. [AHU Coordinator](#6-ahu-coordinator)
7. [Extended Kalman Filter (EKF) — State Estimator](#7-extended-kalman-filter-ekf--state-estimator)
8. [EnergyPlus Co-simulation Interface](#8-energyplus-co-simulation-interface)
9. [Simulation Setup & Weather](#9-simulation-setup--weather)
10. [Output Logging & Analysis](#10-output-logging--analysis)
11. [Performance Metrics & Compliance Criteria](#11-performance-metrics--compliance-criteria)
12. [File Structure Reference](#12-file-structure-reference)
13. [How to Run](#13-how-to-run)

---

## 1. Project Overview

This project implements a **decentralised HVAC control scheme** for a 5-zone commercial office building simulated in **EnergyPlus**. Control is co-executed in **Python** via the EnergyPlus Python API, enabling real-time actuator overrides at every simulation timestep.

**Key design goals:**
- Each zone controller sees **only its own measurements** (true decentralisation)
- A lightweight **central AHU coordinator** resolves system-wide conflicts
- An **Extended Kalman Filter (EKF)** runs per-zone for state and parameter estimation
- The climate context is **Colombo, Sri Lanka** (hot-humid tropical, year-round cooling)

**Technology Stack:**

| Layer | Technology |
|---|---|
| Building physics | EnergyPlus (IDF model) |
| Control logic | Python 3 (`pyenergyplus` API) |
| State estimation | NumPy-based EKF |
| Data analysis | pandas, matplotlib |
| Weather | EPW file — Colombo, Sri Lanka |

---

## 2. System Architecture

```
+------------------------------------------------------------------+
|                        EnergyPlus Engine                         |
|   (MultiZone_VAV_PythonControl.idf + Colombo.epw)                |
|                                                                   |
|  Zone 1 --+                                                       |
|  Zone 2 --+  VAV Air Terminals  -->  AHU (DX Coil + OA Damper)   |
|  Zone 3 --+                                                       |
|  Zone 4 --+                                                       |
|  Zone 5 --+                                                       |
+-------------------------+-----------------------------------------+
                          | Python API callback (every zone timestep)
                          v
+------------------------------------------------------------------+
|                       Orchestrator (main.py)                      |
|                                                                   |
|  READ sensors -->  [Zone 1 PI + EKF]  --+                        |
|                    [Zone 2 PI + EKF]  --+                        |
|                    [Zone 3 PI + EKF]  --+-->  AHU Coordinator    |
|                    [Zone 4 PI + EKF]  --+          |              |
|                    [Zone 5 PI + EKF]  --+          |              |
|                                                    v              |
|  WRITE actuators <-------------- sat_sp, oa_flow                 |
|  (mdot per zone, coolSP per zone)                                |
|                                                    |              |
|  LOG --> out/control_log.csv                                     |
+------------------------------------------------------------------+
```

**Timestep loop (inside `Orchestrator.on_timestep`):**

```
Step 1 - READ:   T, w (humidity ratio), RH, CO2 from all zones
Step 2 - LOCAL:  Each ZoneController runs its PI law independently
Step 3 - COORD:  AHUCoordinator aggregates requests -> sat_sp, oa_flow
Step 4 - WRITE:  mdot and cooling setpoint written per zone; AHU commands set
Step 5 - LOG:    Everything written to control_log.csv
```

---

## 3. Building & Zone Configuration

The EnergyPlus model (`MultiZone_VAV_PythonControl.idf`) contains 5 zones served by a single VAV AHU system with individual air terminals.

### Zone Parameters

| Zone | Use | Max Flow (m³/s) | Max mdot (kg/s) | Kp | Ki | Cool SP | Heat SP | RH Target |
|---|---|---|---|---|---|---|---|---|
| Zone 1 | Open Office | 0.50 | **0.60** | 0.15 | 0.008 | 24 °C | 18 °C | 55% |
| Zone 2 | Private Offices | 0.35 | **0.42** | 0.15 | 0.008 | 24 °C | 18 °C | 55% |
| Zone 3 | Conference Room | 0.55 | **0.66** | 0.20 | 0.010 | 24 °C | 18 °C | 55% |
| Zone 4 | Server Room | 0.60 | **0.72** | 0.25 | 0.012 | 24 °C | 18 °C | 50% |
| Zone 5 | Reception | 0.35 | **0.42** | 0.15 | 0.008 | 24 °C | 18 °C | 55% |

> **Note:** `max_mdot = max_flow_m3s × rho_air` where `rho_air = 1.2 kg/m³`

### Global Constants

| Constant | Value | Description |
|---|---|---|
| `CO2_SETPOINT` | 800 ppm | Central coordinator CO₂ target |
| `OUTDOOR_CO2` | 400 ppm | Background outdoor CO₂ |
| `SAT_FLOOR` | 10 °C | Minimum allowed supply air temperature |
| `RHO_AIR` | 1.2 kg/m³ | Air density for flow conversion |

---

## 4. Control Philosophy — Decentralised + Coordinated

### Decentralised Control (per-zone)

Each zone controller is a **fully independent agent**. It receives only:
- Zone mean air temperature `T` [°C]
- Zone humidity ratio `w` [kg/kg]
- Zone relative humidity `RH` [%]
- Zone CO₂ concentration `c` [ppm]

It outputs a **request** to the AHU:
- Desired supply mass flow rate `mdot` [kg/s]
- Desired supply air temperature `t_sup_req` [°C]
- Its current CO₂ level `co2` [ppm]
- Local cooling setpoint `cool_sp` [°C]

### Centralised Coordination (AHU level)

The AHU coordinator sees **all zone requests** and resolves:
1. **Supply air temperature** — serve the most demanding zone
2. **Outdoor air flow** — proportional to the worst CO₂ zone

This is a **hierarchical two-level control** architecture:
- **Level 1:** Local PI controllers (zone level) — fast, responsive, decentralised
- **Level 2:** AHU coordinator (system level) — lightweight aggregation rules

---

## 5. Zone-Level PI Controller

### PI Control Law

The controller drives supply air mass flow rate `u = mdot` to maintain zone temperature at setpoint.

**Error definition** (positive when too warm → need more cooling):

```
e(t) = T_zone(t) - T_setpoint
```

**Continuous PI law:**

```
u(t) = Kp * e(t) + Ki * integral[ e(tau) dtau ]
```

**Discrete form** (each simulation timestep dt seconds):

```
integral_k = integral_{k-1} + e_k * dt

u_raw = Kp * e_k + Ki * integral_k

mdot = clamp(u_raw, 0, mdot_max)
```

### Anti-Windup — Conditional Integration (Clamping Method)

Without anti-windup, when the actuator saturates (e.g. fully open VAV damper) the integrator keeps accumulating error, causing severe overshoot when the zone re-enters the normal range.

**Clamping strategy:** The integrator update is only accepted if the output is **not saturated**, or if saturation is in the **opposite direction** to integrator growth.

```python
integral_candidate = self._integral + err * dt
u_raw = Kp * err + Ki * integral_candidate

saturated_high = (u_raw >= max_mdot) and (err > 0)
saturated_low  = (u_raw <= 0.0)     and (err < 0)

if not (saturated_high or saturated_low):
    self._integral = integral_candidate
# else: freeze the integrator at its current value
```

**Anti-windup in words:**
- If zone is too hot AND output is already at maximum → don't keep accumulating the +ve error
- If zone is too cold AND output is already at minimum → don't keep accumulating the −ve error
- In all other cases (including partial saturation), allow integration normally

### Humidity-Based SAT Request

Each zone adjusts its supply air temperature request based on local RH:

```
rh_err = RH - rh_target
if rh_err <= 5.0%:
    t_sup_req = 14.0 °C   (normal cooling)
elif rh_err <= 10.0%:
    t_sup_req = 14.0 to 13.0 °C   (mild dehumidification)
else:
    t_sup_req = 13.0 to 12.0 °C   (aggressive dehumidification)
```

This is a **sliding scale humidity override with a 5% dead-band** on the SAT request. The dead-band prevents the tropical background humidity from permanently locking the AHU into dehumidification mode.

### Zone 4 Override — Server Room Safety Floor

The Server Room runs 24/7 with constant high equipment loads. Its controller enforces a **minimum airflow floor** regardless of temperature error:

```
mdot_Zone4 = max(mdot_PI, 0.30 * mdot_max_Zone4)
```

This prevents the fan from ever cutting off completely in a critical environment.

---

## 6. AHU Coordinator

The `AHUCoordinator` receives the list of all zone requests each timestep and computes two system-level commands.

### Supply Air Temperature Setpoint (SAT)

The AHU must supply air cold enough for the **most-demanding zone**. The most demanding zone is the one requesting the lowest `t_sup_req`:

```
T_SAT = max(T_SAT_floor, min over all zones of t_sup_req_z)
```

Where `T_SAT_floor = 10 °C` prevents excessive over-cooling.

**In practice:**
- Any zone with `RH > rh_target` requests 12 °C → SAT drops to 12 °C for all zones
- If no zone has high humidity, SAT stays at 14 °C
- SAT can never go below 10 °C (floor safety limit)

### Outdoor Air (OA) Flow Rate

OA is scaled proportionally to the worst-case zone CO₂ concentration — a simplified **demand-controlled ventilation (DCV)** strategy:

```
phi_OA = (c_max - c_outdoor) / (c_setpoint - c_outdoor)

phi_OA = clamp(phi_OA, 0.15, 1.0)

mdot_OA = phi_OA * sum(mdot_z for all zones)
```

Where:
- `c_max` = highest CO₂ among all zones [ppm]
- `c_outdoor` = 400 ppm (ambient background)
- `c_setpoint` = 800 ppm (controller target)
- `0.15` = minimum OA fraction (15% fresh air at all times, for code compliance)

**Interpretation:**

| CO₂ level | phi_OA | Meaning |
|---|---|---|
| 400 ppm (outdoor only) | 0.0 → clamped to 0.15 | Minimum ventilation |
| 600 ppm (midway) | 0.50 | 50% of total flow is OA |
| 800 ppm (at setpoint) | 1.00 | Full OA ventilation |
| >800 ppm (above target) | clamped to 1.00 | Maximum OA |

---

## 7. Extended Kalman Filter (EKF) — State Estimator

### Purpose

Each zone runs its own **per-zone EKF** to simultaneously:
1. **Filter** noisy sensor readings of T, humidity ratio `w`, and CO₂ `c`
2. **Estimate hidden physical parameters** that cannot be directly measured

### Augmented State Vector

```
x = [ T,   w,   c,          <- measured/observable states
      C_T, U, C_w, k, q_occ ]  <- hidden parameters
```

| Symbol | Description | Units |
|---|---|---|
| T | Zone mean air temperature | °C |
| w | Zone humidity ratio | kg/kg |
| c | Zone CO₂ concentration | ppm |
| C_T | Thermal capacitance of zone air | J/K |
| U | Overall heat transfer coefficient (fabric losses) | W/K |
| C_w | Moisture capacitance | kg |
| k | CO₂ generation coefficient | ppm·m³/s |
| q_occ | Occupancy-related internal heat gain | W |

### EKF Equations

**Prediction step:**

```
x_pred = f(x_k-1, u_k, dt)        [nonlinear state transition]
F_k    = df/dx at x_k-1            [Jacobian of f]

x^-    = x_pred
P^-    = F_k * P_{k-1} * F_k^T + Q
```

**Update step (measurement fusion):**

```
z_k = [T_measured, w_measured, c_measured]

y   = z_k - h(x^-)                  [innovation]
S   = H * P^- * H^T + R             [innovation covariance]
K   = P^- * H^T * S^-1              [Kalman gain]

x_k = x^- + K * y                   [posterior estimate]
P_k = (I - K*H) * P^-               [posterior covariance]
```

### Physical Sub-Model Equations (for `ekf.py` implementation)

The state transition function `f(x, u, dt)` encodes three zone energy/mass balances:

**Thermal balance:**
```
C_T * dT/dt = mdot * cp * (T_sup - T) - U * (T - T_out) + q_int + q_occ

T_{k+1} = T_k + (dt/C_T) * [mdot*cp*(T_sup - T_k) - U*(T_k - T_out) + q_int + q_occ]
```

**Moisture balance:**
```
C_w * dw/dt = mdot * (w_sup - w) + mdot_occ * w_gen

w_{k+1} = w_k + (dt/C_w) * [mdot * (w_sup - w_k) + moisture_generation]
```

**CO₂ mass balance:**
```
V * dc/dt = mdot * (c_sup - c) + k * N_occ

c_{k+1} = c_k + (dt/V) * [mdot * (c_sup - c_k) + k * N_occ]
```

Where `V` is zone volume [m³] and `N_occ` is estimated occupant count (derived from `q_occ`).

### Hidden Parameter Dynamics (Random Walk)

The hidden parameters `(C_T, U, C_w, k, q_occ)` vary slowly. Their dynamics are modelled as a **random walk**:

```
theta_{k+1} = theta_k + noise(0, Q_theta)
```

This allows the EKF to slowly track changes in occupancy, building fabric, or equipment loads without requiring an explicit schedule.

### EKF Initialisation (default for ~40 m² zone)

| Variable | Values |
|---|---|
| x₀ | T=24°C, w=0.010, c=500 ppm; C_T=3×10⁵, U=50, C_w=2×10⁴, k=0.01, q_occ=0 |
| P₀ (diagonal) | [0.5, 1e-6, 100, 1e9, 100, 1e6, 1e-3, 1.0] |
| Q (diagonal) | [0.01, 1e-9, 1.0, 1e6, 1.0, 1e3, 1e-5, 0.1] |
| R (diagonal) | [0.1, 1e-7, 25.0] — for T [°C], w [kg/kg], CO₂ [ppm] sensors |

> **Status:** The `predict()` and `update()` methods in `estimation/ekf.py` are scaffold stubs. The EKF is structurally defined but the Jacobian and physics functions are pending full implementation. The simulation falls back gracefully — if EKF raises `NotImplementedError`, `est=None` is returned and PI control still operates normally.

---

## 8. EnergyPlus Co-simulation Interface

### API Handles Resolved at Simulation Start

| Handle Key | EnergyPlus Object | Type | Node / Zone |
|---|---|---|---|
| `sat_sp` | System Node Setpoint | Actuator | DX Coil Outlet Node |
| `oa_flow` | Outdoor Air Controller | Actuator | VAV OA Controller |
| `T:{zone}` | Zone Mean Air Temperature | Variable | per zone |
| `w:{zone}` | Zone Air Humidity Ratio | Variable | per zone |
| `rh:{zone}` | Zone Air Relative Humidity | Variable | per zone |
| `co2:{zone}` | Zone Air CO2 Concentration | Variable | per zone |
| `mdot:{zone}` | AirTerminal:SingleDuct:ConstantVolume:NoReheat | Actuator | per terminal |
| `csp:{zone}` | Zone Temperature Control | Actuator (Cooling SP) | per zone |

### Callback Registration

```python
api.runtime.callback_end_zone_timestep_after_zone_reporting(state, orch.on_timestep)
```

Fires **after each zone reporting timestep** — Python gets access to freshly computed zone states before EnergyPlus advances to the next timestep.

### Actuator Write Order (each timestep)

1. `mdot` per zone → VAV terminal mass flow rate [kg/s], clamped to `[0, max_mdot]`
2. `cool_sp` per zone → zone temperature cooling setpoint [°C]
3. `sat_sp` → AHU supply air temperature setpoint [°C]
4. `oa_flow` → AHU outdoor air mass flow rate [kg/s]

---

## 9. Simulation Setup & Weather

| Parameter | Value |
|---|---|
| Building model | `model/MultiZone_VAV_PythonControl.idf` |
| Weather file | `model/Colombo.epw` |
| Climate | Hot-humid tropical (Köppen: Aw) — Colombo, Sri Lanka |
| Typical outdoor temp | 27–33 °C year-round |
| Typical outdoor RH | 70–85% |
| Output directory | `out/` |
| Control log | `out/control_log.csv` |

**Why Colombo?**
- Cooling is required year-round (virtually no heating load)
- High latent loads — humidity is the dominant HVAC challenge
- The SAT humidity-override (12 °C vs 14 °C) is frequently triggered
- CO₂ control is the primary fresh-air driver (no economiser benefit from cold outdoor air)

---

## 10. Output Logging & Analysis

### control_log.csv Schema

One row per simulation timestep (typically every 10 minutes of simulated time):

| Column | Description | Units |
|---|---|---|
| `datetime` | `MM-DD HH:MM` simulation timestamp | — |
| `sim_hours` | Total elapsed simulation hours | h |
| `{Zone}_T` | Zone mean air temperature | °C |
| `{Zone}_w` | Zone humidity ratio | kg/kg |
| `{Zone}_rh` | Zone relative humidity | % |
| `{Zone}_co2` | Zone CO₂ concentration | ppm |
| `{Zone}_mdot_cmd` | Commanded supply mass flow | kg/s |
| `{Zone}_coolSP_cmd` | Commanded cooling setpoint | °C |
| `AHU_SAT_cmd` | AHU supply air temperature setpoint | °C |
| `AHU_OA_cmd` | AHU outdoor air mass flow | kg/s |

Where `{Zone}` is one of: Zone1, Zone2, Zone3, Zone4, Zone5.

### Visualisation (`visualize.py`)

Generates 3 interactive dark-themed Matplotlib figures, each filtered to a selected month (`MONTH_TO_PLOT`):

1. **Temperature** — All 5 zones over time, with 24 °C setpoint reference line
2. **Relative Humidity** — All 5 zones
3. **CO₂** — All 5 zones, with 1000 ppm ASHRAE 62.1 indicative limit

Each plot includes:
- Per-zone coloured line + semi-transparent area fill
- 2-day rolling mean overlay (dashed line, window = 288 samples)
- Stats annotation box: mean / min / max per zone

**Zone colour scheme:**

| Zone | Hex | Description |
|---|---|---|
| Zone 1 | `#4FC3F7` | cyan-blue |
| Zone 2 | `#AED581` | lime-green |
| Zone 3 | `#FFB74D` | amber |
| Zone 4 | `#CE93D8` | purple |
| Zone 5 | `#F06292` | rose-pink |

### Analysis Script (`analyse_results.py`)

Prints a terminal report with sections:

1. **Temperature Report** — mean, std, min, max; % within ±1 °C and ±2 °C of 24 °C; % above setpoint
2. **CO₂ Report** — mean, max; % below 800 ppm and below 1000 ppm (ASHRAE limit)
3. **Humidity Report** — mean, max; % below / above 60% comfort limit
4. **Airflow Utilisation** — mean + max flow vs capacity; average utilisation %
5. **AHU Commands** — SAT distribution (% time at each discrete level); OA flow stats

---

## 11. Performance Metrics & Compliance Criteria

### Temperature Comfort

| Metric | Target | Notes |
|---|---|---|
| Cooling setpoint | 24.0 °C | All zones |
| Tight band (±1 °C) | Maximise | Good control quality |
| Wide band (±2 °C) | Maximise | Minimum acceptable |
| % above setpoint | Minimise | Indicates comfort violations |

### Air Quality (CO₂)

| Metric | Target | Standard |
|---|---|---|
| Controller setpoint | < 800 ppm | Project design target |
| ASHRAE 62.1 limit | < 1000 ppm | Industry standard |
| Minimum OA fraction | ≥ 15% | Code minimum (enforced by clamp) |

### Humidity

| Metric | Target |
|---|---|
| Comfort zone RH | < 60% for all zones |
| Zone 4 (Server Room) RH | < 50% |
| Dehumidification trigger | RH > rh_target → SAT request = 12 °C |

### Airflow

| Metric | Description |
|---|---|
| Flow range | 0 to max_mdot per zone |
| Zone 4 minimum | Always ≥ 30% of max_mdot (server room safety) |
| Utilisation | `mean_flow / max_flow * 100%` |

---

## 12. File Structure Reference

```
3YP/
|
+-- main.py                        # Driver: EnergyPlus API + Orchestrator loop
+-- config.py                      # Zone parameters & global constants
+-- visualize.py                   # Interactive Matplotlib plots (3 figures)
+-- analyse_results.py             # Terminal performance summary report
+-- PROJECT_OVERVIEW.md            # This documentation file
+-- requirements.txt               # Python dependencies (pandas, matplotlib, numpy)
|
+-- controllers/
|   +-- zone_controller.py         # Base PI + EKF + anti-windup logic (ZoneController)
|   +-- ahu.py                     # AHU coordinator (SAT + OA rules)
|   +-- zone1.py                   # Zone 1 - Open Office (standard, inherits base)
|   +-- zone2.py                   # Zone 2 - Private Offices (standard)
|   +-- zone3.py                   # Zone 3 - Conference Room (standard)
|   +-- zone4.py                   # Zone 4 - Server Room (min-flow safety override)
|   +-- zone5.py                   # Zone 5 - Reception (standard)
|
+-- estimation/
|   +-- ekf.py                     # Extended Kalman Filter (scaffold; impl. pending)
|
+-- model/
|   +-- MultiZone_VAV_PythonControl.idf   # 5-zone EnergyPlus building model
|   +-- 1Zone_SriLanka_Controlled.idf     # Single-zone prototype (legacy / reference)
|   +-- Colombo.epw                       # Weather data: Colombo, Sri Lanka
|
+-- out/                           # Simulation outputs (auto-generated)
|   +-- control_log.csv            # Primary results: Python-written log
|   +-- eplusout.eso               # EnergyPlus native binary output
|   +-- eplusout.err               # Simulation warnings/errors
|   +-- eplustbl.htm               # EnergyPlus summary HTML report
|   +-- ... (other .bnd, .eio, .rdd files)
|
+-- docs/
|   +-- EnergyPlus_Model_Overview.md.pdf
|   +-- Teamventus MID Evaluation_Final.pdf
|
+-- venv/                          # Python virtual environment
```

---

## 13. How to Run

### Prerequisites
- EnergyPlus installed (v24.x or v25.x)
- `pyenergyplus` on `PYTHONPATH` (ships with EnergyPlus install, under `pyenergyplus/`)
- Python virtual environment with dependencies installed

### Step-by-Step

```powershell
# 1. Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 2. Install dependencies (first time only)
pip install -r requirements.txt

# 3. Run the simulation (generates out/control_log.csv)
python main.py

# 4. Visualise results (opens 3 interactive plot windows)
python visualize.py

# 5. Print performance summary to terminal
python analyse_results.py
```

### Optional: Enable EnergyPlus Native CSV Output

Set `EPLUS_ROOT` in `main.py` to your EnergyPlus installation path:

```python
EPLUS_ROOT = r"C:\EnergyPlusV25-2-0"
```

This enables the `-r` flag, which runs `ReadVarsESO` post-processing and generates `out/eplusout.csv` in addition to our custom `control_log.csv`.

---

## Appendix — Equation Quick Reference

| Quantity | Formula |
|---|---|
| Temperature error | `e = T_zone - T_setpoint` |
| PI output | `u = Kp * e + Ki * integral(e dt)` |
| Discrete integration | `I_k = I_{k-1} + e_k * dt` |
| Anti-windup condition | Accept I update only if output NOT saturated in error direction |
| Actuator clamping | `mdot = clamp(u, 0, mdot_max)` |
| Zone 4 minimum flow | `mdot_4 = max(mdot_PI, 0.30 * mdot_max_4)` |
| Humidity SAT request | `t_sup = 12°C if RH > target, else 14°C` |
| AHU SAT setpoint | `T_SAT = max(10, min_z(t_sup_req_z))` |
| OA fraction | `phi = clamp( (c_max - 400)/(800 - 400), 0.15, 1.0 )` |
| OA mass flow | `mdot_OA = phi * sum(mdot_z)` |
| EKF predict | `x^- = f(x, u, dt);  P^- = F P F^T + Q` |
| EKF update | `K = P^- H^T (H P^- H^T + R)^-1;  x = x^- + K*(z - h(x^-))` |
| Thermal balance | `C_T * dT/dt = mdot*cp*(T_sup-T) - U*(T-T_out) + q_int + q_occ` |
| Moisture balance | `C_w * dw/dt = mdot*(w_sup - w) + moisture_gen` |
| CO2 balance | `V * dc/dt = mdot*(c_sup - c) + k * N_occ` |

---

*Generated from project source code — ME325 3YP, University of Peradeniya.*
