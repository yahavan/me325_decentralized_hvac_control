"""
analyse_results.py
==================
Reads out/control_log.csv and prints a comprehensive performance summary:
  - Temperature compliance (% within +-1C and +-2C of setpoint)
  - CO2 compliance (% below 800 ppm target and 1000 ppm ASHRAE limit)
  - Relative humidity compliance (% below 60%)
  - Airflow utilisation per zone
  - AHU supply air temperature and OA flow statistics

Run with:
    python analyse_results.py
"""

import os
import pandas as pd

LOG_PATH   = os.path.join("out", "control_log.csv")
COOL_SP    = 24.0    # degC cooling setpoint
CO2_TARGET = 800.0   # ppm -- controller target
CO2_LIMIT  = 1000.0  # ppm -- ASHRAE 62.1 indicative limit
RH_LIMIT   = 60.0    # % relative humidity comfort limit

MAX_MDOT = {         # kg/s -- from config.py
    "Zone1": 0.60,
    "Zone2": 0.42,
    "Zone3": 0.66,
    "Zone4": 0.72,
    "Zone5": 0.42,
}

ZONE_USE = {
    "Zone1": "Open Office",
    "Zone2": "Private Offices",
    "Zone3": "Conference Room",
    "Zone4": "Server Room",
    "Zone5": "Reception",
}


def load(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot find '{path}'. Run main.py first.")
    df = pd.read_csv(path)
    print(f"Loaded {len(df):,} rows  |  "
          f"{df['datetime'].iloc[0]}  to  {df['datetime'].iloc[-1]}\n")
    return df


def sep(title=""):
    width = 70
    if title:
        pad = (width - len(title) - 2) // 2
        print("=" * pad + f" {title} " + "=" * (width - pad - len(title) - 2))
    else:
        print("=" * width)


def pct(series, condition):
    return condition.mean() * 100


def temperature_report(df):
    sep("TEMPERATURE  (setpoint = 24 C)")
    print(f"{'Zone':<8} {'Use':<18} {'Mean':>6} {'Std':>5} {'Min':>6} {'Max':>6} "
          f"{'w/in+/-1C':>10} {'w/in+/-2C':>10} {'AboveSP':>8}")
    print("-" * 80)
    for z, use in ZONE_USE.items():
        col = f"{z}_T"
        s = df[col]
        mean = s.mean(); std = s.std(); mn = s.min(); mx = s.max()
        w1    = pct(s, (s >= COOL_SP - 1) & (s <= COOL_SP + 1))
        w2    = pct(s, (s >= COOL_SP - 2) & (s <= COOL_SP + 2))
        above = pct(s, s > COOL_SP)
        print(f"{z:<8} {use:<18} {mean:6.2f} {std:5.2f} {mn:6.2f} {mx:6.2f} "
              f"{w1:9.1f}% {w2:9.1f}% {above:7.1f}%")
    print()


def co2_report(df):
    sep("CO2  (target=800 ppm | ASHRAE limit=1000 ppm)")
    print(f"{'Zone':<8} {'Use':<18} {'Mean':>6} {'Max':>7} "
          f"{'<800ppm':>8} {'<1000ppm':>9}")
    print("-" * 65)
    for z, use in ZONE_USE.items():
        col = f"{z}_co2"
        s = df[col]
        mean = s.mean(); mx = s.max()
        ok800  = pct(s, s < CO2_TARGET)
        ok1000 = pct(s, s < CO2_LIMIT)
        flag = " WARNING" if ok1000 < 100 else " OK"
        print(f"{z:<8} {use:<18} {mean:6.0f} {mx:7.0f} "
              f"{ok800:7.1f}% {ok1000:8.1f}%{flag}")
    print()


def humidity_report(df):
    sep("RELATIVE HUMIDITY  (comfort limit = 60 %)")
    print(f"{'Zone':<8} {'Use':<18} {'Mean':>6} {'Max':>6} {'<60%':>8} {'>60%':>8}")
    print("-" * 60)
    for z, use in ZONE_USE.items():
        col = f"{z}_rh"
        s = df[col]
        mean = s.mean(); mx = s.max()
        ok   = pct(s, s < RH_LIMIT)
        over = pct(s, s >= RH_LIMIT)
        print(f"{z:<8} {use:<18} {mean:6.1f} {mx:6.1f} {ok:7.1f}% {over:7.1f}%")
    print()


def airflow_report(df):
    sep("AIRFLOW UTILISATION")
    print(f"{'Zone':<8} {'Use':<18} {'Mean kg/s':>10} {'Max kg/s':>9} "
          f"{'Cap kg/s':>9} {'AvgUtil':>8}")
    print("-" * 70)
    for z, use in ZONE_USE.items():
        col  = f"{z}_mdot_cmd"
        s    = df[col]
        mean = s.mean(); mx = s.max(); cap = MAX_MDOT[z]
        util = (mean / cap) * 100
        ever_zero = (s == 0).any()
        note = "  (never zero)" if not ever_zero else ""
        print(f"{z:<8} {use:<18} {mean:10.4f} {mx:9.4f} {cap:9.2f} {util:7.1f}%{note}")
    print()


def ahu_report(df):
    sep("AHU COMMANDS")
    sat = df["AHU_SAT_cmd"]
    oa  = df["AHU_OA_cmd"]
    print("  Supply Air Temperature (SAT setpoint):")
    print(f"    Mean={sat.mean():.2f} C   Min={sat.min():.2f} C   Max={sat.max():.2f} C")
    for val in sorted(sat.unique()):
        print(f"    At {val:.0f} C : {pct(sat, sat == val):.1f}% of timesteps")
    print()
    print("  Outdoor Air Flow:")
    print(f"    Mean={oa.mean():.4f} kg/s   Min={oa.min():.4f} kg/s   Max={oa.max():.4f} kg/s")
    print()


if __name__ == "__main__":
    df = load(LOG_PATH)
    temperature_report(df)
    co2_report(df)
    humidity_report(df)
    airflow_report(df)
    ahu_report(df)
    sep()
    print("Done.")
