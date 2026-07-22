"""
simulate.py — Pure-Python HVAC Zone Physics Simulation (Full Year)
===================================================================
Simulates 5 zones using first-principles ODEs (no EnergyPlus required).

Physics models per zone:
  Thermal : C_T · dT/dt = mdot·cp·(T_sup - T) + UA·(T_out - T) + q_int
  Moisture: C_w · dw/dt = mdot·(w_sup - w) + m_occ
  CO₂     : V·rho · dc/dt = mdot·(c_sup - c) + G_occ

Control law (P-controller, same as main.py):
  mdot = clamp(kp · (T - cool_sp), 0, 1) · max_mdot

Outputs: out/sim_data.json  (consumed by dashboard.html)

Run with:
    python simulate.py
"""

import json
import math
import os

# ─────────────────────────── CONSTANTS ───────────────────────────
CP_AIR   = 1006.0   # J/(kg·K)  specific heat of air
RHO_AIR  = 1.2      # kg/m³
DT       = 60.0     # seconds per timestep (1 minute)
SIM_DAYS = 365      # full year

# ─────────────────────────── WEATHER ──────────────────────────────
# Colombo full-year climate model
# Two monsoon seasons:
#   SW monsoon: May–Sept  (hot & very humid)
#   NE monsoon: Oct–Jan   (warm & humid, some rain)
#   Inter-monsoons: Feb–Apr, transitional (hot & drier)

# Monthly mean daily temperatures for Colombo (°C)
#              J     F     M     A     M     J     J     A     S     O     N     D
_TMEAN = [27.0, 27.5, 28.5, 29.0, 29.0, 28.0, 27.5, 27.5, 28.0, 28.0, 27.5, 27.0]
_TAMP  = [ 4.5,  5.0,  5.0,  4.5,  4.0,  3.5,  3.5,  3.5,  4.0,  4.0,  4.0,  4.5]  # daily amplitude

# Monthly mean humidity ratio (kg/kg) — higher during monsoons
#              J      F      M      A      M      J      J      A      S      O      N      D
_WMEAN = [0.019, 0.018, 0.018, 0.019, 0.021, 0.022, 0.022, 0.022, 0.021, 0.020, 0.020, 0.019]

_DAYS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def _month_of_year(day_of_year):
    """Return 0-indexed month for a given 0-indexed day of year."""
    acc = 0
    for i, d in enumerate(_DAYS_PER_MONTH):
        acc += d
        if day_of_year < acc:
            return i
    return 11

def outdoor_temp(t_sec):
    """Colombo outdoor temperature with seasonal + diurnal variation."""
    day  = int(t_sec / 86400) % 365
    hour = (t_sec / 3600.0) % 24
    mo   = _month_of_year(day)
    # Diurnal: min at ~05:00, max at ~14:00
    return _TMEAN[mo] + _TAMP[mo] * math.sin(math.pi * (hour - 5) / 12 - math.pi/2)

def outdoor_humidity(t_sec):
    """Humidity ratio kg/kg — higher during SW/NE monsoon seasons."""
    day = int(t_sec / 86400) % 365
    mo  = _month_of_year(day)
    return _WMEAN[mo]

# ─────────────────────────── OCCUPANCY ────────────────────────────
def occupancy(zone_use, t_sec):
    """Fraction of max occupancy. Weekends are empty for offices."""
    day_of_year  = int(t_sec / 86400)
    day_of_week  = day_of_year % 7   # 0=Mon … 4=Fri, 5=Sat, 6=Sun
    hour         = (t_sec / 3600.0) % 24
    is_weekend   = day_of_week >= 5

    if zone_use == "Server Room":
        return 0.15   # servers run 24/7
    if is_weekend:
        return 0.05   # nearly empty on weekends
    if 8 <= hour < 9:
        return 0.5
    if 9 <= hour < 12:
        return 1.0
    if 12 <= hour < 13:
        return 0.4
    if 13 <= hour < 17:
        return 0.9
    if 17 <= hour < 18:
        return 0.3
    return 0.0

# ─────────────────────────── ZONE DEFINITIONS ─────────────────────
# Matches design spec table exactly:
#   n_occ_max: people count from spec (8, 4, 12, 1, 5)
#   q_equip:   equipment heat load W (lights 10W/m² + equip from spec)
#   infiltration: 0.0003 m³/s per zone (uniform, from spec)
INFILT_M3S = 0.0003   # m³/s — uniform leakage all zones

ZONE_PHYSICS = {
    "Zone 1": dict(area=80.0, height=3.0, U_wall=1.2, n_occ_max=8,  q_equip=2160,
                   infilt=INFILT_M3S, use="Open Office",     colour="#4FC3F7"),
    # q_equip = lights(10W/m²×80) + office equip(12W/m²×80) = 800+960=1760, +400 base = ~2160
    "Zone 2": dict(area=50.0, height=3.0, U_wall=1.2, n_occ_max=4,  q_equip=950,
                   infilt=INFILT_M3S, use="Private Offices", colour="#AED581"),
    # lights(9W/m²×50) + office(10W/m²×50) = 450+500 = 950
    "Zone 3": dict(area=60.0, height=3.0, U_wall=1.2, n_occ_max=12, q_equip=780,
                   infilt=INFILT_M3S, use="Conference Room", colour="#FFB74D"),
    # lights(8W/m²×60) + equip(5W/m²×60) = 480+300 = 780
    "Zone 4": dict(area=40.0, height=3.0, U_wall=0.8, n_occ_max=1,  q_equip=2640,
                   infilt=INFILT_M3S, use="Server Room",     colour="#CE93D8"),
    # lights(6W/m²×40) + server equip(60W/m²×40) = 240+2400 = 2640
    "Zone 5": dict(area=30.0, height=3.0, U_wall=1.4, n_occ_max=5,  q_equip=510,
                   infilt=INFILT_M3S, use="Reception",       colour="#F06292"),
    # lights(11W/m²×30) + equip(6W/m²×30) = 330+180 = 510
}

# Controller config (must stay in sync with config.py)
ZONE_CTRL = {
    "Zone 1": dict(max_flow_m3s=0.50, cool_sp=24.0, rh_target=55.0, kp=0.15),
    "Zone 2": dict(max_flow_m3s=0.35, cool_sp=24.0, rh_target=55.0, kp=0.15),
    "Zone 3": dict(max_flow_m3s=0.55, cool_sp=23.0, rh_target=55.0, kp=0.20),  # 23°C per spec
    "Zone 4": dict(max_flow_m3s=0.60, cool_sp=21.0, rh_target=50.0, kp=0.25),  # 21°C per spec
    "Zone 5": dict(max_flow_m3s=0.35, cool_sp=24.0, rh_target=55.0, kp=0.15),
}
for k, v in ZONE_CTRL.items():
    v["max_mdot"] = v["max_flow_m3s"] * RHO_AIR

CO2_SETPOINT = 800.0
OUTDOOR_CO2  = 400.0
SAT_FLOOR    = 10.0
C_SUP        = 400.0   # ppm CO₂ in supply air

# ─────────────────────────── SIMULATION ───────────────────────────
class Zone:
    def __init__(self, name):
        self.name  = name
        phys       = ZONE_PHYSICS[name]
        ctrl       = ZONE_CTRL[name]

        self.area  = phys["area"]
        self.h     = phys["height"]
        self.vol   = phys["area"] * phys["height"]
        self.U_tot = phys["U_wall"] * (2*(phys["area"] + phys["height"]*10))  # rough envelope UA W/K
        self.n_max = phys["n_occ_max"]
        self.q_eqp = phys["q_equip"]
        self.infilt = phys["infilt"]   # infiltration m³/s
        self.use   = phys["use"]

        # Thermal capacitance: air + furniture approximation
        self.C_T   = RHO_AIR * self.vol * CP_AIR * 8.0   # ×8 for furniture mass

        # Moisture capacitance
        self.C_w   = RHO_AIR * self.vol * 5.0

        # Controller params
        self.kp       = ctrl["kp"]
        self.cool_sp  = ctrl["cool_sp"]
        self.rh_tgt   = ctrl["rh_target"]
        self.max_mdot = ctrl["max_mdot"]
        self.server_min = 0.30 * self.max_mdot if name == "Zone 4" else 0.0

        # State
        self.T   = 26.0     # °C
        self.w   = 0.018    # kg/kg humidity ratio
        self.co2 = 450.0    # ppm
        self.mdot = 0.0
        self.rh  = 70.0

    def rh_from_w_T(self, w, T):
        """Approximate relative humidity from w and T (Magnus formula)."""
        Psat = 610.78 * math.exp(17.27 * T / (T + 237.3))  # Pa
        P    = 101325.0
        w_sat = 0.622 * Psat / (P - Psat)
        return min(100.0, 100.0 * w / max(w_sat, 1e-9))

    def step(self, t_sec, T_sup, dt):
        occ  = occupancy(self.use, t_sec)
        n    = occ * self.n_max
        T_out = outdoor_temp(t_sec)
        w_out = outdoor_humidity(t_sec)

        # Infiltration mass flow rate (kg/s): 0.0003 m³/s × ρ_air
        mdot_infilt = self.infilt * RHO_AIR   # kg/s of outdoor air leaking in

        # ── P-controller ──────────────────────────────────────────
        err   = self.T - self.cool_sp
        mdot  = min(max(0.0, self.kp * err), 1.0) * self.max_mdot
        mdot  = max(mdot, self.server_min)    # server room floor
        self.mdot = mdot

        # Supply humidity: dehumidified if above target
        w_sup = 0.008 if self.rh > self.rh_tgt else 0.011

        # ── Thermal ODE ──────────────────────────────────────────
        q_conv   = mdot * CP_AIR * (T_sup - self.T)          # supply air
        q_env    = self.U_tot * (T_out - self.T)              # envelope conduction
        q_infilt = mdot_infilt * CP_AIR * (T_out - self.T)   # infiltration heat
        q_occ    = n * 75.0                                   # 75 W/person sensible
        q_int    = self.q_eqp + q_occ
        dT       = (q_conv + q_env + q_infilt + q_int) / self.C_T * dt
        self.T   = self.T + dT

        # ── Moisture ODE ─────────────────────────────────────────
        m_occ    = n * 50e-6          # ~50 g/h per person = 1.4e-5 kg/s
        m_infilt = mdot_infilt * (w_out - self.w)   # infiltration moisture
        dw       = (mdot * (w_sup - self.w) + m_occ + m_infilt) / self.C_w * dt
        self.w   = max(0.005, self.w + dw)
        self.rh  = self.rh_from_w_T(self.w, self.T)

        # ── CO₂ ODE ──────────────────────────────────────────────
        G_occ    = n * 5.0e-6        # ~5 ml/s per person (0.3 L/min)
        mass_air = RHO_AIR * self.vol
        # infiltration brings in outdoor CO₂ (400 ppm) and dilutes indoor CO₂
        dc_infilt = mdot_infilt * (OUTDOOR_CO2 - self.co2) / mass_air
        dc        = (mdot * (C_SUP - self.co2) / mass_air + G_occ * 1e6 / mass_air
                     + dc_infilt) * dt
        self.co2  = max(400.0, self.co2 + dc)

        return dict(T=round(self.T, 3), w=round(self.w, 5),
                    rh=round(self.rh, 2), co2=round(self.co2, 1),
                    mdot=round(self.mdot, 4))


def ahu_coordinate(zone_states, zone_mdots):
    """Lightweight AHU: same logic as controllers/ahu.py"""
    # SAT: coldest request (drive by RH if high)
    t_sup_requests = []
    for zs in zone_states.values():
        t_sup_requests.append(12.0 if zs["rh"] > 55.0 else 14.0)
    sat = max(SAT_FLOOR, min(t_sup_requests))

    # OA: scale by worst CO₂
    co2_max  = max(zs["co2"] for zs in zone_states.values())
    tot_mdot = sum(zone_mdots.values())
    oa_frac  = (co2_max - OUTDOOR_CO2) / (CO2_SETPOINT - OUTDOOR_CO2)
    oa_frac  = min(1.0, max(0.15, oa_frac))
    oa_flow  = round(oa_frac * tot_mdot, 4)
    return dict(sat_sp=round(sat, 2), oa_flow=oa_flow)


def run_simulation():
    zones     = {name: Zone(name) for name in ZONE_PHYSICS}
    n_steps   = int(SIM_DAYS * 24 * 3600 / DT)
    T_sup     = 13.0   # initial supply air temperature

    records = []
    print(f"Running simulation: {SIM_DAYS} day(s), {n_steps} timesteps @ {DT}s each …")

    for step in range(n_steps):
        t_sec = step * DT
        hour  = t_sec / 3600.0

        zone_results = {}
        zone_mdots   = {}
        for name, zone in zones.items():
            res = zone.step(t_sec, T_sup, DT)
            zone_results[name] = res
            zone_mdots[name]   = res["mdot"]

        ahu = ahu_coordinate(zone_results, zone_mdots)
        T_sup = ahu["sat_sp"]

        if step % 30 == 0:  # save every 30 min (every 30 timesteps)
            day_of_year = int(t_sec / 86400)
            records.append(dict(
                t_min  = round(hour * 60, 1),
                hour   = round(hour, 3),
                day    = day_of_year,
                T_out  = round(outdoor_temp(t_sec), 2),
                zones  = zone_results,
                ahu    = ahu,
            ))

        # progress report every 30 simulated days
        if step % (30 * 24 * 60) == 0:
            day_of_year = int(t_sec / 86400)
            pct = 100 * step / n_steps
            print(f"  Day {day_of_year:>3d}/365  ({pct:5.1f}%)  records so far: {len(records):,}")

    print(f"Simulation done — {len(records)} data points generated.")
    return records, ZONE_PHYSICS


def main():
    os.makedirs("out", exist_ok=True)
    records, zone_meta = run_simulation()

    # Build metadata for dashboard
    metadata = {
        "zones": {
            name: {
                "use":      ZONE_PHYSICS[name]["use"],
                "colour":   ZONE_PHYSICS[name]["colour"],
                "cool_sp":  ZONE_CTRL[name]["cool_sp"],
                "max_mdot": ZONE_CTRL[name]["max_mdot"],
            }
            for name in ZONE_PHYSICS
        },
        "dt_min": DT / 60.0,
        "sim_days": SIM_DAYS,
        "co2_setpoint": CO2_SETPOINT,
    }

    out = dict(metadata=metadata, records=records)
    path = os.path.join("out", "sim_data.json")
    with open(path, "w") as f:
        json.dump(out, f, separators=(",", ":"))

    size_kb = os.path.getsize(path) / 1024
    print(f"Data written to {path}  ({size_kb:.1f} KB)")
    print("Now open  dashboard.html  in your browser to view the interactive visualisation.")


if __name__ == "__main__":
    main()
