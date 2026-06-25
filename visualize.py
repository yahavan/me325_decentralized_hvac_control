"""
visualize.py — Rich multi-zone HVAC data visualiser
====================================================
Reads   : out/control_log.csv
Outputs : Three interactive Matplotlib figures (Temperature, Humidity, CO₂),
          one for each metric, each showing all 5 zones on the same axes.

Run with:
    python visualize.py
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
import numpy as np

# ─────────────────────────── CONFIG ───────────────────────────
LOG_PATH      = os.path.join("out", "control_log.csv")
MONTH_TO_PLOT = 1   # 1 = January … 12 = December

# Colour palette – one distinct colour per zone
ZONE_COLOURS = {
    "Zone1": "#4FC3F7",   # cyan-blue
    "Zone2": "#AED581",   # lime-green
    "Zone3": "#FFB74D",   # amber
    "Zone4": "#CE93D8",   # purple
    "Zone5": "#F06292",   # rose-pink
}

ZONES   = list(ZONE_COLOURS.keys())
N_ZONES = len(ZONES)

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
    "lines.linewidth":   1.5,
    "lines.antialiased": True,
})

# ─────────────────────── DATA LOADING ─────────────────────────
def load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        sys.exit(f"[ERROR] Cannot find '{path}'. Run main.py first to generate the simulation data.")

    df = pd.read_csv(path)

    # Parse month from the 'datetime' column (format: MM-DD HH:MM)
    # and filter to the selected month.
    df["_month"] = df["datetime"].str.split("-").str[0].astype(int)
    df = df[df["_month"] == MONTH_TO_PLOT].copy()
    df.drop(columns=["_month"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    month_names = ["January","February","March","April","May","June",
                   "July","August","September","October","November","December"]
    print(f"Loaded {len(df):,} rows from '{path}' (filtered to {month_names[MONTH_TO_PLOT-1]}).")
    print(f"Columns: {list(df.columns)}")
    return df


def make_x_labels(df: pd.DataFrame) -> list[str]:
    """
    Create readable x-axis tick labels from the 'datetime' column.
    Returns a list of strings like 'Jan 01', 'Jan 15', etc.
    """
    month_abbr = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
    labels = []
    for s in df["datetime"]:
        try:
            parts  = s.strip().split()
            md     = parts[0].split("-")
            mo, dy = int(md[0]), int(md[1])
            labels.append(f"{month_abbr[mo-1]} {dy:02d}")
        except Exception:
            labels.append(s)
    return labels


# ─────────────────────── PLOT FACTORY ─────────────────────────
def plot_metric(
    df:        pd.DataFrame,
    col_suffix: str,
    ylabel:    str,
    title:     str,
    fig_title: str,
    unit_label: str,
    setpoint_line: float | None = None,
    setpoint_label: str = "",
) -> None:
    """Draw a single figure for one metric across all 5 zones."""

    x = df["sim_hours"].values

    fig, ax = plt.subplots(figsize=(18, 7))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_PANEL)

    # ── Plot each zone ──
    for zone, colour in ZONE_COLOURS.items():
        col = f"{zone}_{col_suffix}"
        if col not in df.columns:
            print(f"[WARN] Column '{col}' not found – skipping.")
            continue
        y = df[col].values

        # Thin semi-transparent fill between the line and its rolling mean
        # 288 samples ≈ 2 days at 10-min resolution
        rolling = pd.Series(y).rolling(window=288, min_periods=1, center=True).mean().values
        ax.fill_between(x, rolling, y, alpha=0.07, color=colour, linewidth=0)
        ax.plot(x, y,       color=colour, linewidth=1.3, alpha=0.85, label=zone)
        ax.plot(x, rolling, color=colour, linewidth=0.7, alpha=0.45, linestyle="--")

    # ── Optional setpoint reference line ──
    if setpoint_line is not None:
        ax.axhline(setpoint_line, color="#FF5252", linewidth=1.4,
                   linestyle=":", alpha=0.9, label=setpoint_label)

    # ── X-axis: convert sim_hours to day markers ──
    hours_per_day = 24
    max_hours     = float(x.max())
    num_days      = int(max_hours // hours_per_day) + 1

    # Show a tick every 7 days (or fewer if the run is short)
    step = 7 if num_days > 30 else (1 if num_days <= 7 else 2)
    tick_hours  = np.arange(0, max_hours + 1, step * hours_per_day)

    month_abbr = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]

    def hours_to_label(h):
        # Simulate 01-01 start
        total_minutes = int(h * 60)
        year_minutes  = 365 * 24 * 60
        total_minutes = total_minutes % year_minutes
        doy = total_minutes // (24 * 60)          # day of year (0-indexed)
        # rough month / day
        days_per_month = [31,28,31,30,31,30,31,31,30,31,30,31]
        month, day = 0, doy
        for i, d in enumerate(days_per_month):
            if day < d:
                month = i
                break
            day -= d
        return f"{month_abbr[month]} {day+1:02d}"

    tick_labels = [hours_to_label(h) for h in tick_hours]
    ax.set_xticks(tick_hours)
    ax.set_xticklabels(tick_labels, rotation=45, ha="right", fontsize=9)

    # ── Labels & styling ──
    ax.set_xlim(x[0], x[-1])
    ax.set_xlabel("Date", fontsize=12, labelpad=8)
    ax.set_ylabel(ylabel, fontsize=12, labelpad=8)

    # ── Spines ──
    for spine in ax.spines.values():
        spine.set_edgecolor(GRID_COL)
        spine.set_linewidth(0.8)

    # ── Legend ──
    handles, labels = ax.get_legend_handles_labels()
    # Add a dashed line for "rolling mean" explanation
    dummy_mean = Line2D([0], [0], color="white", linewidth=0.7,
                        linestyle="--", alpha=0.5, label="2-day rolling mean")
    handles.append(dummy_mean)
    labels.append("2-day rolling mean")
    ax.legend(handles=handles, labels=labels,
              loc="upper right", fontsize=10,
              facecolor="#1A1D27", framealpha=0.6, edgecolor=GRID_COL)

    # ── Titles ──
    ax.set_title(title, fontsize=15, fontweight="bold",
                 color=TITLE_COL, pad=14)
    fig.suptitle(fig_title, fontsize=11, color="#9E9E9E", y=0.995)

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
    stats_text = "\n".join(stats_lines)
    ax.text(
        0.01, 0.97, stats_text,
        transform=ax.transAxes,
        fontsize=8.5, verticalalignment="top",
        fontfamily="monospace", color="#BDBDBD",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#0E1117",
                  edgecolor=GRID_COL, alpha=0.75),
    )

    plt.tight_layout(rect=[0, 0, 1, 0.97])


# ──────────────────────────── MAIN ────────────────────────────
def main():
    df = load_data(LOG_PATH)

    # ── 1) TEMPERATURE ──
    plot_metric(
        df            = df,
        col_suffix    = "T",
        ylabel        = "Zone Mean Air Temperature (°C)",
        title         = "Zone Temperature Variation — All 5 Zones",
        fig_title     = "ME325 Decentralised HVAC Control · EnergyPlus Simulation Results",
        unit_label    = "°C",
        setpoint_line = 24.0,
        setpoint_label= "Cooling Setpoint (24 °C)",
    )

    # ── 2) RELATIVE HUMIDITY ──
    plot_metric(
        df         = df,
        col_suffix = "rh",
        ylabel     = "Zone Air Relative Humidity (%)",
        title      = "Zone Relative Humidity Variation — All 5 Zones",
        fig_title  = "ME325 Decentralised HVAC Control · EnergyPlus Simulation Results",
        unit_label = "%",
    )

    # ── 3) CO₂ CONCENTRATION ──
    plot_metric(
        df            = df,
        col_suffix    = "co2",
        ylabel        = "Zone Air CO₂ Concentration (ppm)",
        title         = "Zone CO₂ Concentration Variation — All 5 Zones",
        fig_title     = "ME325 Decentralised HVAC Control · EnergyPlus Simulation Results",
        unit_label    = "ppm",
        setpoint_line = 1000.0,
        setpoint_label= "ASHRAE 62.1 indicative limit (1000 ppm)",
    )

    print("\nDisplaying plots — close each window to proceed to the next.\n")
    plt.show()


if __name__ == "__main__":
    main()
