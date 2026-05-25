"""
controller.py
=============
EnergyPlus Python API co-simulation controller for a 10x10x3m
single-zone room in Colombo, Sri Lanka.

Place this file at the ROOT of your project folder:

  your_project/
  ├── controller.py          <- this file goes here
  ├── models/
  │   └── 1Zone_SriLanka_Controlled.idf
  ├── weather/
  │   └── <any .epw file>    <- auto-detected, no hardcoding needed
  ├── output/                <- created automatically, results go here
  ├── others/
  ├── venv/
  └── .gitignore

What it does each 15-min timestep
----------------------------------
  READ    Zone Mean Air Temperature   (deg C)
          Zone Air Relative Humidity  (%)
          Zone Air CO2 Concentration  (ppm)

  COMPUTE Required cooling mass-flow via cascade proportional law

  WRITE   Ideal-Loads actuator -> Air Mass Flow Rate (kg/s)

Usage (activate your venv first)
---------------------------------
  venv\\Scripts\\activate        # Windows
  python controller.py
"""

import sys
import os
import math
import csv
import glob

# ---------------------------------------------------------------------------
# PATH RESOLUTION
# BASE_DIR is wherever this script lives (project root).
# Everything else is found relative to it automatically.
# ---------------------------------------------------------------------------

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
WEATHER_DIR= os.path.join(BASE_DIR, "weather")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOG_CSV    = os.path.join(OUTPUT_DIR, "controller_log.csv")

# --- IDF: pick the first .idf found in models/ ---
_idf_candidates = glob.glob(os.path.join(MODELS_DIR, "*.idf"))
IDF_FILE = _idf_candidates[0] if _idf_candidates else None

# --- EPW: pick the first .epw found in weather/ (no hardcoded filename) ---
_epw_candidates = glob.glob(os.path.join(WEATHER_DIR, "*.epw"))
EPW_FILE = _epw_candidates[0] if _epw_candidates else None

# ---------------------------------------------------------------------------
# ENERGYPLUS INSTALL — adjust this one path to match your machine
# The pyenergyplus package ships inside the EnergyPlus install folder.
# ---------------------------------------------------------------------------

ENERGYPLUS_INSTALL = r"C:\EnergyPlusV26-1-0"   # <-- only line you may need to change

sys.path.insert(0, ENERGYPLUS_INSTALL)

# ---------------------------------------------------------------------------
# STARTUP VALIDATION
# Catch missing files/folders before EnergyPlus launches so the error
# message is clear rather than a cryptic C++ crash.
# ---------------------------------------------------------------------------

def _validate_paths():
    errors = []

    ep_api = os.path.join(ENERGYPLUS_INSTALL, "pyenergyplus", "api.py")
    if not os.path.isfile(ep_api):
        errors.append(
            f"pyenergyplus not found at: {ENERGYPLUS_INSTALL}\n"
            f"  -> Update ENERGYPLUS_INSTALL in this script."
        )

    if not IDF_FILE or not os.path.isfile(IDF_FILE):
        errors.append(
            f"No .idf file found in: {MODELS_DIR}\n"
            f"  -> Copy 1Zone_SriLanka_Controlled.idf into the models/ folder."
        )
    
    if not EPW_FILE or not os.path.isfile(EPW_FILE):
        errors.append(
            f"No .epw weather file found in: {WEATHER_DIR}\n"
            f"  -> Download a Colombo EPW from energyplus.net/weather\n"
            f"     and place it in the weather/ folder."
        )

    if errors:
        print("\n" + "=" * 70)
        print("  STARTUP ERROR — fix the following before running:")
        print("=" * 70)
        for e in errors:
            print(f"\n  ❌  {e}")
        print("=" * 70 + "\n")
        sys.exit(1)

_validate_paths()

# Safe to import now
from pyenergyplus.api import EnergyPlusAPI  # noqa: E402

# ---------------------------------------------------------------------------
# CONTROL SETPOINTS
# ---------------------------------------------------------------------------

T_SETPOINT  = 24.0    # degC  target zone temperature
T_DEADBAND  =  0.5    # degC  no action within +/- deadband of setpoint
RH_MAX      = 65.0    # %     humidity comfort ceiling
CO2_MAX     = 1000.0  # ppm   ventilation trigger (ASHRAE 62.1)

# Supply air conditions (must match IDF IdealLoads min cooling values)
T_SUPPLY    = 14.0    # degC
W_SUPPLY    = 0.010   # kg_water/kg_dryair  (~95% RH at 14 degC)

# Physical constants
CP_AIR      = 1006.0  # J/(kg.K)
HFG         = 2_501_000  # J/kg  latent heat of vaporisation

# Actuator limits — must match IDF Maximum Cooling Air Flow Rate
MDOT_MIN    = 0.02    # kg/s  always-on minimum ventilation
MDOT_MAX    = 2.00    # kg/s  hardware ceiling

# Proportional gains
KP_TEMP     = 0.20    # kg/s per degC above setpoint
KP_CO2      = 5e-4    # kg/s per ppm above CO2_MAX

# ---------------------------------------------------------------------------
# PSYCHROMETRIC HELPERS
# ---------------------------------------------------------------------------

def _psat(T_C: float) -> float:
    """Saturation vapour pressure [Pa] via Magnus formula."""
    return 611.2 * math.exp(17.67 * T_C / (T_C + 243.5))

def humidity_ratio(T_C: float, RH_pct: float, P: float = 101_325.0) -> float:
    """Humidity ratio W [kg_water/kg_dryair]."""
    Pv = (RH_pct / 100.0) * _psat(T_C)
    return 0.622 * Pv / (P - Pv)

def cooling_power(mdot: float, T_zone: float, RH_zone: float) -> dict:
    """
    Instantaneous cooling load removed by supply air [W].
      Q_sens = mdot * Cp * (T_zone - T_supply)
      Q_lat  = mdot * hfg * (W_zone - W_supply)
    """
    W_zone = humidity_ratio(T_zone, RH_zone)
    q_s = mdot * CP_AIR * max(0.0, T_zone - T_SUPPLY)
    q_l = mdot * HFG   * max(0.0, W_zone - W_SUPPLY)
    return {"sensible_W": q_s, "latent_W": q_l, "total_W": q_s + q_l}

# ---------------------------------------------------------------------------
# CONTROL LAW
# ---------------------------------------------------------------------------

def compute_mdot(T_zone: float, RH_zone: float, CO2_ppm: float) -> float:
    """
    Cascade proportional controller -> supply air mass-flow [kg/s].

      1. Temperature error  -> primary cooling flow
      2. CO2 excess         -> additional ventilation flow
      3. High RH override   -> clamp to 50% max to dehumidify
      4. Hard clamp to [MDOT_MIN, MDOT_MAX]
    """
    # Temperature term
    T_error   = T_zone - (T_SETPOINT + T_DEADBAND)
    mdot_temp = max(0.0, KP_TEMP * T_error) + MDOT_MIN

    # CO2 ventilation term
    CO2_excess = max(0.0, CO2_ppm - CO2_MAX)
    mdot_co2   = KP_CO2 * CO2_excess

    mdot = mdot_temp + mdot_co2

    # Humidity override
    if RH_zone > RH_MAX:
        mdot = max(mdot, 0.5 * MDOT_MAX)

    return max(MDOT_MIN, min(MDOT_MAX, mdot))

# ---------------------------------------------------------------------------
# ENERGYPLUS API STATE
# ---------------------------------------------------------------------------

api = EnergyPlusAPI()

_handles = {
    "T"   : -1,   # Zone Mean Air Temperature
    "RH"  : -1,   # Zone Air Relative Humidity
    "CO2" : -1,   # Zone Air CO2 Concentration
    "mdot": -1,   # Actuator: Air Mass Flow Rate
}
_handles_ready   = False
_warmup_complete = False
_csv_file        = None
_csv_writer      = None


def _open_log():
    global _csv_file, _csv_writer
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    _csv_file   = open(LOG_CSV, "w", newline="")
    _csv_writer = csv.writer(_csv_file)
    _csv_writer.writerow([
        "sim_time_hr", "T_zone_C", "RH_zone_pct", "CO2_ppm",
        "mdot_kg_s", "Q_sens_W", "Q_lat_W", "Q_total_W",
    ])


def _resolve_handles(state) -> bool:
    """Request all handles; returns True only when every handle is valid."""
    if _handles["T"] == -1:
        _handles["T"] = api.exchange.get_variable_handle(
            state, "Zone Mean Air Temperature", "ZONE ONE")

    if _handles["RH"] == -1:
        _handles["RH"] = api.exchange.get_variable_handle(
            state, "Zone Air Relative Humidity", "ZONE ONE")

    if _handles["CO2"] == -1:
        _handles["CO2"] = api.exchange.get_variable_handle(
            state, "Zone Air CO2 Concentration", "ZONE ONE")

    if _handles["mdot"] == -1:
        _handles["mdot"] = api.exchange.get_actuator_handle(
            state,
            "Ideal Loads Air System",   # component type  (matches IDF)
            "Air Mass Flow Rate",       # control type
            "Zone1 Ideal Loads",        # unique component name (matches IDF)
        )

    return all(h != -1 for h in _handles.values())

# ---------------------------------------------------------------------------
# CALLBACKS
# ---------------------------------------------------------------------------

def on_warmup_complete(state):
    global _warmup_complete
    _warmup_complete = True
    print("Warmup complete - controller now active.")


def on_timestep_end(state):
    global _handles_ready

    if not _warmup_complete:
        return

    if not _handles_ready:
        _handles_ready = _resolve_handles(state)
        if not _handles_ready:
            print("Handles not ready yet - skipping timestep.")
            return
        print("All handles acquired (T, RH, CO2, actuator).")
        _open_log()

    # READ
    T_zone  = api.exchange.get_variable_value(state, _handles["T"])
    RH_zone = api.exchange.get_variable_value(state, _handles["RH"])
    CO2_ppm = api.exchange.get_variable_value(state, _handles["CO2"])
    t_hr    = api.exchange.current_sim_time(state)

    # COMPUTE
    mdot = compute_mdot(T_zone, RH_zone, CO2_ppm)

    # WRITE
    api.exchange.set_actuator_value(state, _handles["mdot"], mdot)

    # LOG (every timestep to CSV)
    q = cooling_power(mdot, T_zone, RH_zone)
    _csv_writer.writerow([
        f"{t_hr:.4f}",
        f"{T_zone:.2f}",
        f"{RH_zone:.1f}",
        f"{CO2_ppm:.0f}",
        f"{mdot:.4f}",
        f"{q['sensible_W']:.1f}",
        f"{q['latent_W']:.1f}",
        f"{q['total_W']:.1f}",
    ])

    # PRINT to console every simulated hour (every 4th of 4 timesteps/hr)
    if round(t_hr * 4) % 4 == 0:
        flag_T   = "HOT " if T_zone  > T_SETPOINT + T_DEADBAND else "OK  "
        flag_RH  = "WET " if RH_zone > RH_MAX                  else "OK  "
        flag_CO2 = "HIGH" if CO2_ppm > CO2_MAX                 else "OK  "
        print(
            f"[t={t_hr:8.2f}h]  "
            f"T={T_zone:5.1f}C [{flag_T}]  "
            f"RH={RH_zone:4.1f}% [{flag_RH}]  "
            f"CO2={CO2_ppm:5.0f}ppm [{flag_CO2}]  "
            f"-> mdot={mdot:.3f}kg/s  Q={q['total_W']/1000:.2f}kW"
        )

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  EnergyPlus Controller  |  Sri Lanka 10x10x3m Room")
    print("=" * 70)
    print(f"  IDF     : {IDF_FILE}")
    print(f"  Weather : {EPW_FILE}")
    print(f"  Output  : {OUTPUT_DIR}")
    print(f"  Log     : {LOG_CSV}")
    print("-" * 70)
    print(f"  T setpoint : {T_SETPOINT} degC  (deadband +/-{T_DEADBAND} degC)")
    print(f"  RH limit   : {RH_MAX} %")
    print(f"  CO2 limit  : {CO2_MAX} ppm")
    print(f"  Supply air : {T_SUPPLY} degC / W={W_SUPPLY} kg/kg")
    print(f"  Flow range : {MDOT_MIN} - {MDOT_MAX} kg/s")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    state = api.state_manager.new_state()
    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, on_timestep_end)
    api.runtime.callback_after_new_environment_warmup_complete(state, on_warmup_complete)

    exit_code = api.runtime.run_energyplus(
        state,
        ["-w", EPW_FILE, "-d", OUTPUT_DIR, IDF_FILE]
    )

    if _csv_file and not _csv_file.closed:
        _csv_file.flush()
        _csv_file.close()
    api.state_manager.delete_state(state)

    print("-" * 70)
    if exit_code == 0:
        print(f"Done. Log -> {LOG_CSV}")
        print(f"EnergyPlus results -> {OUTPUT_DIR}")
    else:
        print(f"EnergyPlus finished with errors (code {exit_code}).")
        print(f"Check: {os.path.join(OUTPUT_DIR, 'eplusout.err')}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
