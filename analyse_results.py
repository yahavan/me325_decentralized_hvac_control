"""
analyse_results.py
==================
Reads out/control_log.csv and prints a comprehensive performance summary
relevant to the ME325 Decentralised HVAC Control project.

Metrics reported
----------------
1.  Temperature — compliance, discomfort degree-hours, occupied-hours split
2.  CO2         — compliance, max exceedance duration, occupied-hours split
3.  Humidity    — compliance, optimal-band (40-60 %) time
4.  Airflow     — utilisation, saturation %, zero-flow %
5.  AHU         — SAT distribution bands, OA statistics
6.  Occupancy   — daily average headcount per zone
7.  Overall Scorecard — pass/warn/fail per zone + overall grade

Run with:
    python analyse_results.py
"""

import os
import sys
import numpy as np
import pandas as pd

# ─────────────────── CONFIG ────────────────────────────────────────────
LOG_PATH   = os.path.join("out", "control_log.csv")
COOL_SP    = 24.0       # °C  cooling setpoint
CO2_TARGET = 800.0      # ppm  controller target (soft)
CO2_LIMIT  = 1000.0     # ppm  ASHRAE 62.1 indicative limit
RH_OPT_LO  = 40.0      # %   ASHRAE optimal band low
RH_OPT_HI  = 60.0      # %   ASHRAE optimal band high
TIMESTEP_H = 10 / 60   # hours per simulation timestep (10 min)

MAX_MDOT = {            # kg/s — from config.py
    "Zone1": 0.60,
    "Zone2": 0.42,
    "Zone3": 0.66,
    "Zone4": 0.72,
    "Zone5": 0.42,
}

OCC_MAX = {             # peak occupancy caps — from config.py
    "Zone1": 12,
    "Zone2": 6,
    "Zone3": 20,
    "Zone4": 2,
    "Zone5": 8,
}

ZONE_USE = {
    "Zone1": "Open Office",
    "Zone2": "Private Offices",
    "Zone3": "Conference Room",
    "Zone4": "Server Room",
    "Zone5": "Reception",
}

ZONES = list(ZONE_USE.keys())

# ─────────────────── HELPERS ───────────────────────────────────────────
W = 78   # line width

def sep(title=""):
    if title:
        pad = (W - len(title) - 2) // 2
        print("=" * pad + f" {title} " + "=" * (W - pad - len(title) - 2))
    else:
        print("=" * W)


def pct(condition):
    """Percentage of True values in a boolean Series."""
    return condition.mean() * 100


def is_occupied(df):
    """Return a boolean Series: True for Mon-Fri 08:00-18:00 timesteps."""
    # datetime format: "MM-DD HH:MM"
    try:
        # Rebuild a full datetime by assuming year 2007 (EnergyPlus default run)
        parsed = pd.to_datetime("2007-" + df["datetime"].str.replace(" ", " "),
                                format="%Y-%m-%d %H:%M", errors="coerce")
        dow  = parsed.dt.dayofweek  # 0=Mon … 6=Sun
        hour = parsed.dt.hour + parsed.dt.minute / 60.0
        return (dow < 5) & (hour >= 8.0) & (hour < 18.0)
    except Exception:
        # Fallback: assume all occupied if parsing fails
        return pd.Series(True, index=df.index)


def max_consecutive_true(series):
    """Return the maximum number of consecutive True values in a boolean Series."""
    max_run = run = 0
    for v in series:
        if v:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return max_run


def load(path):
    if not os.path.exists(path):
        sys.exit(f"[ERROR] Cannot find '{path}'. Run main.py first.")
    df = pd.read_csv(path)
    print(f"Loaded {len(df):,} rows  |  "
          f"{df['datetime'].iloc[0]}  →  {df['datetime'].iloc[-1]}\n")
    return df


# ─────────────────── 1. TEMPERATURE ────────────────────────────────────
def temperature_report(df, occ):
    sep("TEMPERATURE  —  cooling setpoint = 24 °C")

    hdr = (f"{'Zone':<8} {'Use':<18} {'Mean':>6} {'Std':>5} "
           f"{'±1°C%':>7} {'±2°C%':>7} {'Above%':>7} "
           f"{'DH>SP':>7}  {'Occ±1%':>8}")
    print(hdr)
    print("-" * W)

    for z, use in ZONE_USE.items():
        s = df[f"{z}_T"]
        so = s[occ]

        mean = s.mean()
        std  = s.std()
        w1   = pct((s >= COOL_SP - 1) & (s <= COOL_SP + 1))
        w2   = pct((s >= COOL_SP - 2) & (s <= COOL_SP + 2))
        above = pct(s > COOL_SP)

        # Thermal discomfort degree-hours: sum of (T - setpoint) when T > SP
        dh = ((s[s > COOL_SP] - COOL_SP) * TIMESTEP_H).sum()

        # Occupied-hours ±1°C compliance
        occ_w1 = pct((so >= COOL_SP - 1) & (so <= COOL_SP + 1)) if len(so) > 0 else 0.0

        print(f"{z:<8} {use:<18} {mean:6.2f} {std:5.2f} "
              f"{w1:6.1f}% {w2:6.1f}% {above:6.1f}% "
              f"{dh:7.1f}  {occ_w1:7.1f}%")

    print()
    print("  DH>SP = degree-hours above setpoint (lower is better)")
    print("  Occ±1% = ±1°C compliance during occupied hours only (Mon-Fri 08:00-18:00)")
    print()


# ─────────────────── 2. CO2 ────────────────────────────────────────────
def co2_report(df, occ):
    sep("CO2 CONCENTRATION  —  target 800 ppm | ASHRAE limit 1000 ppm")

    hdr = (f"{'Zone':<8} {'Use':<18} {'Mean':>6} {'Max':>6} "
           f"{'<800%':>7} {'<1000%':>8} {'MaxRun>1k':>10}  {'Occ<800%':>9}")
    print(hdr)
    print("-" * W)

    for z, use in ZONE_USE.items():
        s  = df[f"{z}_co2"]
        so = s[occ]

        mean  = s.mean()
        mx    = s.max()
        ok800  = pct(s < CO2_TARGET)
        ok1000 = pct(s < CO2_LIMIT)

        # Longest continuous exceedance of 1000 ppm (in hours)
        run_steps = max_consecutive_true(s >= CO2_LIMIT)
        run_h     = run_steps * TIMESTEP_H

        # Occupied-hours compliance
        occ_ok = pct(so < CO2_TARGET) if len(so) > 0 else 0.0

        flag = "  ✓" if ok1000 >= 99.9 else ("  !" if ok1000 < 99 else "  ~")
        print(f"{z:<8} {use:<18} {mean:6.0f} {mx:6.0f} "
              f"{ok800:6.1f}% {ok1000:7.1f}% {run_h:9.1f}h  {occ_ok:8.1f}%{flag}")

    print()
    print("  MaxRun>1k = longest continuous stretch above 1000 ppm (hours)")
    print("  ✓ never exceeded | ~ brief exceedance | ! significant exceedance")
    print()


# ─────────────────── 3. HUMIDITY ───────────────────────────────────────
def humidity_report(df):
    sep("RELATIVE HUMIDITY  —  ASHRAE optimal 40–60 %")

    hdr = (f"{'Zone':<8} {'Use':<18} {'Mean':>6} {'Min':>6} {'Max':>6} "
           f"{'Optimal%':>9} {'<40%':>6} {'>60%':>6}")
    print(hdr)
    print("-" * W)

    for z, use in ZONE_USE.items():
        s    = df[f"{z}_rh"]
        mean = s.mean()
        mn   = s.min()
        mx   = s.max()
        opt  = pct((s >= RH_OPT_LO) & (s <= RH_OPT_HI))
        dry  = pct(s < RH_OPT_LO)
        humid = pct(s > RH_OPT_HI)
        print(f"{z:<8} {use:<18} {mean:6.1f} {mn:6.1f} {mx:6.1f} "
              f"{opt:8.1f}% {dry:5.1f}% {humid:5.1f}%")

    print()
    print("  Optimal = time in 40–60 % band (ASHRAE 55 comfort zone)")
    print()


# ─────────────────── 4. AIRFLOW ────────────────────────────────────────
def airflow_report(df):
    sep("AIRFLOW UTILISATION")

    hdr = (f"{'Zone':<8} {'Use':<18} {'Mean':>8} {'Max':>7} {'Cap':>7} "
           f"{'AvgUtil':>8} {'Saturated':>10} {'AtZero':>7}")
    print(hdr)
    print("-" * W)

    for z, use in ZONE_USE.items():
        s   = df[f"{z}_mdot_cmd"]
        cap = MAX_MDOT[z]
        mean = s.mean()
        mx   = s.max()
        util = (mean / cap) * 100
        sat  = pct(s >= cap * 0.99)   # within 1% of cap = saturated
        zero = pct(s <= 0.001)
        print(f"{z:<8} {use:<18} {mean:8.4f} {mx:7.4f} {cap:7.2f} "
              f"{util:7.1f}% {sat:9.1f}% {zero:6.1f}%")

    print()
    print("  Saturated = % of time airflow was at (or within 1% of) maximum capacity")
    print("  AtZero    = % of time airflow command was zero")
    print()


# ─────────────────── 5. AHU ────────────────────────────────────────────
def ahu_report(df):
    sep("AHU COMMANDS")

    sat = df["AHU_SAT_cmd"]
    oa  = df["AHU_OA_cmd"]

    print("  Supply Air Temperature (SAT) setpoint:")
    print(f"    Mean={sat.mean():.2f} °C  |  Std={sat.std():.2f} °C  |  "
          f"Min={sat.min():.2f} °C  |  Max={sat.max():.2f} °C")
    # Distribution in bands (avoid printing every unique float)
    bands = [(10, 11), (11, 12), (12, 13), (13, 14), (14, 15), (15, 20), (20, 30)]
    print("    Temperature bands:")
    for lo, hi in bands:
        p = pct((sat >= lo) & (sat < hi))
        if p > 0.05:
            bar = "#" * int(p / 2)
            print(f"      [{lo:4.0f}–{hi:.0f} °C)  {p:5.1f}%  {bar}")
    print()

    print("  Outdoor Air Mass Flow:")
    print(f"    Mean={oa.mean():.4f} kg/s  |  Std={oa.std():.4f} kg/s  |  "
          f"Min={oa.min():.4f} kg/s  |  Max={oa.max():.4f} kg/s")
    # OA usage bands
    print("    OA flow bands:")
    oa_bands = [(0, 0.1), (0.1, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 5.0)]
    for lo, hi in oa_bands:
        p = pct((oa >= lo) & (oa < hi))
        if p > 0.05:
            bar = "#" * int(p / 2)
            print(f"      [{lo:.1f}–{hi:.1f} kg/s)  {p:5.1f}%  {bar}")
    print()


# ─────────────────── 6. OCCUPANCY ──────────────────────────────────────
def occupancy_report(df):
    sep("OCCUPANCY  —  daily random headcount (from People actuator)")

    hdr = (f"{'Zone':<8} {'Use':<18} {'IDF Default':>12} {'OccMax Cap':>11} "
           f"{'Sim Mean':>9} {'Sim Max':>8} {'Zero%':>7}")
    print(hdr)
    print("-" * W)

    IDF_DEFAULT = {"Zone1": 8, "Zone2": 4, "Zone3": 12, "Zone4": 1, "Zone5": 5}

    for z, use in ZONE_USE.items():
        col = f"{z}_occ"
        if col not in df.columns:
            print(f"{z:<8} {use:<18}  [column not found — run with updated main.py]")
            continue
        s    = df[col]
        mean = s.mean()
        mx   = s.max()
        zero = pct(s == 0)
        idf  = IDF_DEFAULT[z]
        cap  = OCC_MAX[z]
        print(f"{z:<8} {use:<18} {idf:12d} {cap:11d} "
              f"{mean:9.2f} {mx:8.1f} {zero:6.1f}%")

    print()
    print("  Zero% = % of timesteps where occupancy is 0 (nights/weekends expected)")
    print()


# ─────────────────── 7. SCORECARD ──────────────────────────────────────
def scorecard(df, occ):
    sep("OVERALL PERFORMANCE SCORECARD")

    print(f"\n  {'Zone':<8} {'Use':<18} "
          f"{'T±1°C(occ)':>11} {'CO2<800(occ)':>13} {'RH Optimal':>11} "
          f"{'Airflow Sat':>12} {'Grade':>6}")
    print("  " + "-" * (W - 2))

    zone_grades = []
    for z, use in ZONE_USE.items():
        T    = df[f"{z}_T"]
        co2  = df[f"{z}_co2"]
        rh   = df[f"{z}_rh"]
        mdot = df[f"{z}_mdot_cmd"]
        cap  = MAX_MDOT[z]

        To   = T[occ]
        c2o  = co2[occ]

        t_score  = pct((To >= COOL_SP - 1) & (To <= COOL_SP + 1)) if len(To) > 0 else 0.0
        c2_score = pct(c2o < CO2_TARGET) if len(c2o) > 0 else 0.0
        rh_score = pct((rh >= RH_OPT_LO) & (rh <= RH_OPT_HI))
        sat_pct  = pct(mdot >= cap * 0.99)

        # Grade: A ≥ 90 | B ≥ 75 | C ≥ 60 | D < 60
        combined = (t_score * 0.40 + c2_score * 0.35 + rh_score * 0.25)
        if combined >= 90:   grade = "A"
        elif combined >= 75: grade = "B"
        elif combined >= 60: grade = "C"
        else:                grade = "D"

        zone_grades.append(combined)
        print(f"  {z:<8} {use:<18} "
              f"{t_score:10.1f}% {c2_score:12.1f}% {rh_score:10.1f}% "
              f"{sat_pct:11.1f}%  [{grade}]")

    overall = np.mean(zone_grades)
    if overall >= 90:   og = "A"
    elif overall >= 75: og = "B"
    elif overall >= 60: og = "C"
    else:               og = "D"

    print()
    print(f"  Weighting: Temperature 40% | CO2 35% | Humidity 25%")
    print(f"  Overall system score: {overall:.1f}%  →  Grade [{og}]")
    print()
    print("  Grade key:  A ≥ 90%  |  B ≥ 75%  |  C ≥ 60%  |  D < 60%")
    print()

    # Quick compliance summary
    sep("COMPLIANCE SUMMARY")
    print()

    def compliance_line(label, value, thresholds):
        """Print a coloured bar and pass/warn/fail tag."""
        bar_len = int(value / 2)
        bar = "#" * bar_len + "-" * (50 - bar_len)
        tag = "PASS" if value >= thresholds[0] else ("WARN" if value >= thresholds[1] else "FAIL")
        print(f"  {label:<35} {value:5.1f}%  [{bar}]  {tag}")

    # Temperature ±1°C across all zones (occupied hours)
    all_T_occ  = pd.concat([df[f"{z}_T"][occ]  for z in ZONES])
    all_C2_occ = pd.concat([df[f"{z}_co2"][occ] for z in ZONES])
    all_rh     = pd.concat([df[f"{z}_rh"]       for z in ZONES])

    t_all  = pct((all_T_occ  >= COOL_SP - 1) & (all_T_occ  <= COOL_SP + 1))
    c2_all = pct(all_C2_occ  < CO2_TARGET)
    c2_lim = pct(pd.concat([df[f"{z}_co2"] for z in ZONES]) < CO2_LIMIT)
    rh_all = pct((all_rh >= RH_OPT_LO) & (all_rh <= RH_OPT_HI))

    print()
    compliance_line("Temp ±1°C of setpoint (occupied hrs)",  t_all,  (90, 75))
    compliance_line("CO2 below 800 ppm (occupied hrs)",      c2_all, (85, 70))
    compliance_line("CO2 below 1000 ppm (all hours)",        c2_lim, (99, 95))
    compliance_line("RH in 40–60% band (all hours)",         rh_all, (80, 60))
    print()


# ─────────────────── MAIN ──────────────────────────────────────────────
if __name__ == "__main__":
    df  = load(LOG_PATH)
    occ = is_occupied(df)
    occ_pct = occ.mean() * 100
    print(f"  Occupied timesteps (Mon-Fri 08:00-18:00): {occ_pct:.1f}% of total\n")

    temperature_report(df, occ)
    co2_report(df, occ)
    humidity_report(df)
    airflow_report(df)
    ahu_report(df)
    occupancy_report(df)
    scorecard(df, occ)

    sep()
    print("  Done.")
    sep()
