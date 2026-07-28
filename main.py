"""Driver: the ONE process that runs everything.

It owns the EnergyPlus simulation, imports every zone controller + the AHU,
and inside a single timestep callback does: read -> local control (per zone)
-> central coordinate -> write actuators. The controllers are decentralised
because each only receives its own zone's measurements.

Run with:   python main.py
(Requires the EnergyPlus Python API on PYTHONPATH — see notes in chat.)
"""
import csv
import sys
from pyenergyplus.api import EnergyPlusAPI

from config import ZONES
from controllers.ahu import AHUCoordinator
from occupancy import build_occupancy_models
from controllers.zone1 import Zone1Controller
from controllers.zone2 import Zone2Controller
from controllers.zone3 import Zone3Controller
from controllers.zone4 import Zone4Controller
from controllers.zone5 import Zone5Controller
from controllers.zone_controller import ZoneController

IDF = "model/MultiZone_VAV_PythonControl.idf"
EPW = "model/Colombo.epw"
OUTDIR = "out"
LOG = "out/control_log.csv"      # our own results file (always written)

# Set this to your EnergyPlus install folder to let the "-r" flag find
# ReadVarsESO (the folder containing the energyplus executable + PostProcess/).
# Leave as None to skip EnergyPlus's CSV and rely on our self-logger instead.
EPLUS_ROOT = None   # e.g. r"C:\EnergyPlusV25-2-0"

# Map zone name -> controller class. Every zone has its own file.
CONTROLLER_CLASSES = {
    "Zone 1": Zone1Controller,
    "Zone 2": Zone2Controller,
    "Zone 3": Zone3Controller,
    "Zone 4": Zone4Controller,
    "Zone 5": Zone5Controller,
}


def build_controller(cfg):
    cls = CONTROLLER_CLASSES.get(cfg["zone"], ZoneController)
    return cls(cfg)


class Orchestrator:
    def __init__(self, api, state):
        self.api, self.state, self.ex = api, state, api.exchange
        self.ready = False
        self.failed = False
        self.h = {}
        self.controllers = [build_controller(z) for z in ZONES]
        self.ahu = AHUCoordinator(ZONES)
        self.occ_models = build_occupancy_models(ZONES)   # stochastic occupancy
        self._occ_counts = [0.0] * len(ZONES)             # last computed counts
        self._logf = None
        self._log = None

    def _resolve_handles(self):
        ex, st = self.ex, self.state
        # One-time discovery dump: the AUTHORITATIVE list of every readable
        # variable and writable actuator for THIS build. Open it to confirm
        # exact strings if any handle below fails to resolve.
        try:
            with open("available_api_data.csv", "w") as fh:
                fh.write(ex.list_available_api_data_csv(st).decode("utf-8", "replace"))
        except Exception as e:
            print("[warn] could not write available_api_data.csv:", e)

        self.h["sat_sp"] = ex.get_actuator_handle(
            st, "System Node Setpoint", "Temperature Setpoint", "DX Coil Outlet Node")
        self.h["oa_flow"] = ex.get_actuator_handle(
            st, "Outdoor Air Controller", "Air Mass Flow Rate", "VAV OA Controller")
        for z in ZONES:
            k = z["zone"]
            self.h[f"T:{k}"]   = ex.get_variable_handle(st, "Zone Mean Air Temperature", k)
            self.h[f"w:{k}"]   = ex.get_variable_handle(st, "Zone Air Humidity Ratio", k)
            self.h[f"rh:{k}"]  = ex.get_variable_handle(st, "Zone Air Relative Humidity", k)
            self.h[f"co2:{k}"] = ex.get_variable_handle(st, "Zone Air CO2 Concentration", k)
            self.h[f"mdot:{k}"] = ex.get_actuator_handle(
                st, "AirTerminal:SingleDuct:ConstantVolume:NoReheat", "Mass Flow Rate", z["terminal"])
            self.h[f"csp:{k}"]  = ex.get_actuator_handle(
                st, "Zone Temperature Control", "Cooling Setpoint", k)

        # People actuators are NOT used — EnergyPlus drives occupancy from
        # its own IDF schedule. We only mirror it in Python for CSV logging.

        missing = [name for name, hv in self.h.items() if hv == -1]
        if missing:
            print("\n[FATAL] Unresolved handles (look them up in "
                  "available_api_data.csv): " + ", ".join(missing) + "\n")
            self.failed = True
            try:
                self.api.runtime.stop_simulation(self.state)
            except Exception:
                pass
            return
        self.ready = True
        self._open_log()

    def _open_log(self):
        import os
        os.makedirs(OUTDIR, exist_ok=True)
        self._logf = open(LOG, "w", newline="")
        self._log = csv.writer(self._logf)
        cols = ["datetime", "sim_hours"]
        for z in ZONES:
            k = z["zone"].replace(" ", "")
            cols += [f"{k}_T", f"{k}_w", f"{k}_rh", f"{k}_co2",
                     f"{k}_mdot_cmd", f"{k}_coolSP_cmd", f"{k}_occ"]
        cols += ["AHU_SAT_cmd", "AHU_OA_cmd"]
        self._log.writerow(cols)

    def _log_row(self, meas_all, requests, cmd):
        ex, st = self.ex, self.state
        stamp = f"{ex.month(st):02d}-{ex.day_of_month(st):02d} " \
                f"{ex.hour(st):02d}:{ex.minutes(st):02d}"
        row = [stamp, round(ex.current_sim_time(st), 4)]
        for (m, req), occ in zip(zip(meas_all, requests), self._occ_counts):
            row += [round(m["T"], 3), round(m["w"], 5), round(m["rh"], 2),
                    round(m["co2"], 1), round(req["mdot"], 4), req["cool_sp"],
                    round(occ, 2)]
        row += [round(cmd["sat_sp"], 3), round(cmd["oa_flow"], 4)]
        self._log.writerow(row)

    def close(self):
        if self._logf:
            self._logf.close()

    def on_timestep(self, state):
        ex, st = self.ex, self.state
        if self.failed:
            return
        if not self.ready:
            if not ex.api_data_fully_ready(st):
                return
            self._resolve_handles()
            if not self.ready:
                return
        if ex.warmup_flag(st):
            return

        dt = ex.system_time_step(st) * 3600.0  # hours -> seconds

        # 0) OCCUPANCY — mirror the IDF schedule for logging (no actuator write)
        hour       = ex.hour(st) + ex.minutes(st) / 60.0
        ep_dow     = ex.day_of_week(st)   # 1=Sun, 2=Mon … 7=Sat (EnergyPlus)
        for i, (occ_model, z) in enumerate(zip(self.occ_models, ZONES)):
            self._occ_counts[i] = occ_model.step(hour, ep_dow)

        is_weekday = 2 <= ep_dow <= 6   # EnergyPlus: 1=Sun, 2=Mon … 6=Fri, 7=Sat

        # 1) READ + 2) LOCAL CONTROL (decentralised: each gets only its own data)
        requests = []
        meas_all = []
        for ctrl, z in zip(self.controllers, ZONES):
            k = z["zone"]
            meas = dict(
                T=ex.get_variable_value(st, self.h[f"T:{k}"]),
                w=ex.get_variable_value(st, self.h[f"w:{k}"]),
                rh=ex.get_variable_value(st, self.h[f"rh:{k}"]),
                co2=ex.get_variable_value(st, self.h[f"co2:{k}"]),
            )
            meas_all.append(meas)
            requests.append(ctrl.step(meas, dt, hour=hour, is_weekday=is_weekday))

        # 3) CENTRAL COORDINATION
        cmd = self.ahu.coordinate(requests)

        # 4) WRITE actuators
        for ctrl, z, req in zip(self.controllers, ZONES, requests):
            k = z["zone"]
            mdot = min(max(0.0, req["mdot"]), z["max_mdot"])   # kg/s, clamped to ceiling
            ex.set_actuator_value(st, self.h[f"mdot:{k}"], mdot)
            ex.set_actuator_value(st, self.h[f"csp:{k}"], req["cool_sp"])
        ex.set_actuator_value(st, self.h["sat_sp"], cmd["sat_sp"])
        ex.set_actuator_value(st, self.h["oa_flow"], cmd["oa_flow"])

        # 5) LOG everything (incl. our commands, which EnergyPlus's CSV won't have)
        self._log_row(meas_all, requests, cmd)


def main():
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()
    orch = Orchestrator(api, state)
    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, orch.on_timestep)

    args = ["-w", EPW, "-d", OUTDIR, IDF]
    if EPLUS_ROOT:
        # Lets the "-r" post-process find ReadVarsESO when running via the C API.
        api.runtime.set_energyplus_root_directory(state, EPLUS_ROOT)
        args = ["-r"] + args   # also emit EnergyPlus's native eplusout.csv

    try:
        rc = api.runtime.run_energyplus(state, args)
    finally:
        orch.close()           # always flush our control_log.csv
    print(f"\nControl log written to {LOG}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
