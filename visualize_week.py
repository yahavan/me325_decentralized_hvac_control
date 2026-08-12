"""
visualize_week.py — 1-week HVAC data visualiser
================================================
Reads   : out/control_log.csv
Outputs : Three interactive Matplotlib figures (Temperature, Humidity, CO₂)
          filtered to exactly 7 days so individual lines are clearly readable.

Configure the week to display with WEEK_START_MONTH / WEEK_START_DAY below.

Run with:
    python visualize_week.py
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
import numpy as np

# ─────────────────────────── CONFIG ───────────────────────────
LOG_PATH         = os.path.join("out", "control_log.csv")
WEEK_START_MONTH = 3    # Month of the first day of the week to display
WEEK_START_DAY   = 1    # Day-of-month of the first day (e.g. 1 = 1st)
WEEK_DAYS        = 7    # How many days to show (default: 7)

# Colour palette – one distinct colour per zone
ZONE_COLOURS = {
    "Zone1": "#4FC3F7",   # cyan-blue
    "Zone2": "#AED581",   # lime-green
    "Zone3": "#FFB74D",   # amber
    "Zone4": "#CE93D8",   # purple
    "Zone5": "#F06292",   # rose-pink
}

ZONES   = list(ZONE_COLOURS.keys())

# ─────────────────────── STYLE HELPERS ────────────────────────
BG_DARK   = "#0E1117"
BG_PANEL  = "#1A1D27"
GRID_COL  = "#2A2D3A"
TEXT_COL  = "#E0E0E0"
TITLE_COL = "#FFFFFF"

plt.rcParams.update({
    "figure.facecolor":  BG_DARK,
    "axes.facecolor":    BG_PANEL,
    "axes.edgecolor":    GRID_COL,
    "axes.labelcolor":   TEXT_COL,
    "axes.grid":         True,
    "grid.color":        GRID_COL,
    "grid.linewidth":    0.7,
    "grid.alpha":        0.8,
    "xtick.color":       TEXT_COL,
    "ytick.color":       TEXT_COL,
    "text.color":        TEXT_COL,
    "font.family":       "DejaVu Sans",
    "font.size":         11,
    "legend.framealpha": 0.15,
    "legend.edgecolor":  GRID_COL,
    "lines.linewidth":   1.8,       # thicker — fewer data points
    "lines.antialiased": True,
})

# ─────────────────────── DATA LOADING ─────────────────────────
# Days per month (non-leap year) — used to resolve the 7-day window
_DAYS_PER_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def _to_doy(month: int, day: int) -> int:
    """Convert (month, day) to day-of-year (1-indexed)."""
    return sum(_DAYS_PER_MONTH[:month - 1]) + day

def _from_doy(doy: int):
    """Convert day-of-year (1-indexed) back to (month, day)."""
    d = doy - 1
    for i, dm in enumerate(_DAYS_PER_MONTH):
        if d < dm:
            return i + 1, d + 1
        d -= dm
    return 12, 31  # fallback

def load_week(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        sys.exit(f"[ERROR] Cannot find '{path}'. Run main.py first.")

    df = pd.read_csv(path)

    # Parse month and day from "MM-DD HH:MM"
    dt_split  = df["datetime"].str.extract(r"^(\d+)-(\d+)\s+(\d+):(\d+)")
    df["_mo"] = dt_split[0].astype(int)
    df["_dy"] = dt_split[1].astype(int)
    df["_hr"] = dt_split[2].astype(int)
    df["_mn"] = dt_split[3].astype(int)
    df["_doy"] = df.apply(lambda r: _to_doy(int(r["_mo"]), int(r["_dy"])), axis=1)

    start_doy = _to_doy(WEEK_START_MONTH, WEEK_START_DAY)
    end_doy   = start_doy + WEEK_DAYS - 1   # inclusive

    df = df[(df["_doy"] >= start_doy) & (df["_doy"] <= end_doy)].copy()
    df.drop(columns=["_mo", "_dy", "_hr", "_mn", "_doy"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    month_abbr = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
    end_m, end_d = _from_doy(end_doy)
    span = (f"{month_abbr[WEEK_START_MONTH-1]} {WEEK_START_DAY:02d}"
            f" to {month_abbr[end_m-1]} {end_d:02d}")
    print(f"Loaded {len(df):,} rows from '{path}' ({span}).")
    print(f"Columns: {list(df.columns)}")
    return df, span


# ─────────────────────── PLOT FACTORY ─────────────────────────
def plot_metric(
    df:             pd.DataFrame,
    span:           str,
    col_suffix:     str,
    ylabel:         str,
    title:          str,
    unit_label:     str,
    setpoint_line:  float | None = None,
    setpoint_label: str = "",
) -> None:
    """Draw one figure for a single metric across all 5 zones — weekly view."""

    x = df["sim_hours"].values

    fig, ax = plt.subplots(figsize=(16, 6))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_PANEL)

    # Rolling mean window: 1 day at 10-min resolution = 144 samples
    ROLL_WIN = 144

    for zone, colour in ZONE_COLOURS.items():
        col = f"{zone}_{col_suffix}"
        if col not in df.columns:
            print(f"[WARN] Column '{col}' not found – skipping.")
            continue
        y = df[col].values

        rolling = (pd.Series(y)
                   .rolling(window=ROLL_WIN, min_periods=1, center=True)
                   .mean().values)

        ax.fill_between(x, rolling, y, alpha=0.10, color=colour, linewidth=0)
        ax.plot(x, y,       color=colour, linewidth=1.8, alpha=0.90, label=zone)
        ax.plot(x, rolling, color=colour, linewidth=1.0, alpha=0.50, linestyle="--")

    # Optional setpoint reference line
    if setpoint_line is not None:
        ax.axhline(setpoint_line, color="#FF5252", linewidth=1.5,
                   linestyle=":", alpha=0.9, label=setpoint_label)

    # ── X-axis: one tick per day, labelled "Mar 01" ──
    x0          = float(x[0])
    hours_total = float(x[-1]) - x0
    month_abbr  = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]

    # Build one tick per day starting at midnight of each day
    start_doy = _to_doy(WEEK_START_MONTH, WEEK_START_DAY)

    tick_hours = []
    tick_labels = []
    for d in range(WEEK_DAYS + 1):          # +1 so the last day edge shows
        h = x0 + d * 24.0
        if h > x[-1] + 0.1:
            break
        tick_hours.append(h)
        m, dy = _from_doy(start_doy + d)
        tick_labels.append(f"{month_abbr[m-1]} {dy:02d}")

    # Also add 12:00 (noon) minor ticks for readability
    noon_hours = [x0 + d * 24.0 + 12.0 for d in range(WEEK_DAYS)
                  if x0 + d * 24.0 + 12.0 <= x[-1]]
    ax.vlines(noon_hours, ymin=ax.get_ylim()[0], ymax=ax.get_ylim()[1],
              colors=GRID_COL, linewidths=0.4, alpha=0.5)

    ax.set_xticks(tick_hours)
    ax.set_xticklabels(tick_labels, rotation=30, ha="right", fontsize=10)
    ax.set_xlim(x[0], x[-1])

    # ── Labels & styling ──
    ax.set_xlabel("Date", fontsize=12, labelpad=8)
    ax.set_ylabel(ylabel, fontsize=12, labelpad=8)

    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
        spine.set_linewidth(0.8)

    # ── Legend ──
    handles, labels = ax.get_legend_handles_labels()
    dummy_mean = Line2D([0], [0], color="white", linewidth=1.0,
                        linestyle="--", alpha=0.5, label="1-day rolling mean")
    handles.append(dummy_mean)
    labels.append("1-day rolling mean")
    ax.legend(handles=handles, labels=labels,
              loc="upper right", fontsize=10,
              facecolor="#1A1D27", framealpha=0.6, edgecolor=GRID_COL)

    # ── Titles ──
    ax.set_title(title, fontsize=14, fontweight="bold",
                 color=TITLE_COL, pad=12)
    fig.suptitle(
        f"ME325 Decentralised HVAC Control · {span}",
        fontsize=10, color="#9E9E9E", y=0.995,
    )

    # ── Stats annotation ──
    stats_lines = []
    for zone in ZONES:
        col = f"{zone}_{col_suffix}"
        if col in df.columns:
            mn = df[col].mean()
            mx = df[col].max()
            mi = df[col].min()
            stats_lines.append(
                f"{zone:>5s}: mean={mn:6.2f}  min={mi:6.2f}  max={mx:6.2f} {unit_label}"
            )
    ax.text(
        0.01, 0.97, "\n".join(stats_lines),
        transform=ax.transAxes,
        fontsize=8.5, verticalalignment="top",
        fontfamily="monospace", color="#BDBDBD",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#0E1117",
                  edgecolor=GRID_COL, alpha=0.75),
    )

    plt.tight_layout(rect=[0, 0, 1, 0.97])


# ──────────────────────────── MAIN ────────────────────────────
def main():
    df, span = load_week(LOG_PATH)

    if df.empty:
        sys.exit(
            f"[ERROR] No data found for {WEEK_START_MONTH:02d}-{WEEK_START_DAY:02d} "
            f"+ {WEEK_DAYS} days.  Check WEEK_START_MONTH / WEEK_START_DAY in the script."
        )

    # 1) TEMPERATURE
    plot_metric(
        df=df, span=span,
        col_suffix="T",
        ylabel="Zone Mean Air Temperature (°C)",
        title="Zone Temperature — Weekly View (All 5 Zones)",
        unit_label="°C",
        setpoint_line=24.0,
        setpoint_label="Cooling Setpoint (24 °C)",
    )

    # 2) RELATIVE HUMIDITY
    plot_metric(
        df=df, span=span,
        col_suffix="rh",
        ylabel="Zone Air Relative Humidity (%)",
        title="Zone Relative Humidity — Weekly View (All 5 Zones)",
        unit_label="%",
    )

    # 3) CO₂ CONCENTRATION
    plot_metric(
        df=df, span=span,
        col_suffix="co2",
        ylabel="Zone Air CO₂ Concentration (ppm)",
        title="Zone CO₂ Concentration — Weekly View (All 5 Zones)",
        unit_label="ppm",
        setpoint_line=1000.0,
        setpoint_label="ASHRAE 62.1 indicative limit (1000 ppm)",
    )

    print("\nDisplaying plots — close each window to proceed to the next.\n")
    plt.show()


if __name__ == "__main__":
    main()
