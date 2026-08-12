"""
results_summary.py  —  ME325 Decentralised HVAC Control
=========================================================
Graphical results presentation across FOUR separate windows:

  Figure 1  —  Performance Scorecard  (zone grades + aggregate KPIs)
  Figure 2  —  Temperature results  (compliance bars + full-year time-series)
  Figure 3  —  CO₂ and Humidity results
  Figure 4  —  Airflow & AHU system behaviour

Run with:
    python results_summary.py

Outputs:
    Interactive windows  +  out/fig1_scorecard.png  through  out/fig4_ahu.png
"""

import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches

# ─────────────────────────── CONFIG ─────────────────────────────────────────
LOG_PATH   = os.path.join("out", "control_log.csv")
COOL_SP    = 24.0
CO2_TARGET = 800.0
CO2_LIMIT  = 1000.0
RH_OPT_LO  = 40.0
RH_OPT_HI  = 60.0
TIMESTEP_H = 10 / 60

MAX_MDOT = {"Zone1": 0.60, "Zone2": 0.42, "Zone3": 0.66, "Zone4": 0.72, "Zone5": 0.42}

ZONE_USE = {
    "Zone1": "Open Office",
    "Zone2": "Private Offices",
    "Zone3": "Conference Room",
    "Zone4": "Server Room",
    "Zone5": "Reception",
}
ZONES = list(ZONE_USE.keys())

ZONE_COLOURS = {
    "Zone1": "#4FC3F7",
    "Zone2": "#AED581",
    "Zone3": "#FFB74D",
    "Zone4": "#CE93D8",
    "Zone5": "#F06292",
}

# ─────────────────────────── PALETTE ────────────────────────────────────────
BG      = "#0D1117"
PANEL   = "#161B22"
CARD    = "#1C2128"
BORDER  = "#30363D"
TEXT    = "#E6EDF3"
DIM     = "#8B949E"
WHITE   = "#FFFFFF"
GREEN   = "#3FB950"
AMBER   = "#E3B341"
RED     = "#F85149"
BLUE    = "#58A6FF"

plt.rcParams.update({
    "figure.facecolor":  BG,
    "axes.facecolor":    PANEL,
    "axes.edgecolor":    BORDER,
    "axes.labelcolor":   TEXT,
    "axes.titlecolor":   WHITE,
    "axes.grid":         True,
    "grid.color":        BORDER,
    "grid.linewidth":    0.6,
    "grid.alpha":        0.5,
    "xtick.color":       TEXT,
    "ytick.color":       TEXT,
    "xtick.labelsize":   12,
    "ytick.labelsize":   12,
    "axes.labelsize":    13,
    "axes.titlesize":    16,
    "text.color":        TEXT,
    "font.family":       "DejaVu Sans",
    "legend.framealpha": 0.25,
    "legend.edgecolor":  BORDER,
    "legend.facecolor":  CARD,
    "legend.fontsize":   11,
})

# ─────────────────────────── HELPERS ─────────────────────────────────────────
def pct(cond):
    return cond.mean() * 100

def is_occupied(df):
    try:
        parsed = pd.to_datetime(
            "2007-" + df["datetime"].str.strip(),
            format="%Y-%m-%d %H:%M", errors="coerce"
        )
        dow  = parsed.dt.dayofweek
        hour = parsed.dt.hour + parsed.dt.minute / 60.0
        return (dow < 5) & (hour >= 8.0) & (hour < 18.0)
    except Exception:
        return pd.Series(True, index=df.index)

def grade_col(s):
    if s >= 90: return GREEN
    if s >= 75: return AMBER
    return RED

def status_col(v, p, w):
    if v >= p: return GREEN
    if v >= w: return AMBER
    return RED

def spine(ax, col=BORDER):
    for s in ax.spines.values():
        s.set_edgecolor(col)
        s.set_linewidth(0.9)

def fig_title(fig, title, subtitle=""):
    fig.text(0.5, 0.97, title, ha="center", va="top",
             fontsize=20, fontweight="bold", color=WHITE)
    if subtitle:
        fig.text(0.5, 0.945, subtitle, ha="center", va="top",
                 fontsize=12, color=DIM)

def save(fig, name):
    os.makedirs("out", exist_ok=True)
    path = os.path.join("out", name)
    fig.savefig(path, dpi=180, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    print(f"  Saved -> {path}")

# ─────────────────────────── LOAD ────────────────────────────────────────────
def load(path):
    if not os.path.exists(path):
        sys.exit(f"[ERROR] '{path}' not found. Run main.py first.")
    df = pd.read_csv(path)
    print(f"  Loaded {len(df):,} rows | {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    return df

# ─────────────────────────── METRICS ─────────────────────────────────────────
def compute_metrics(df, occ):
    m = {}
    for z in ZONES:
        T    = df[f"{z}_T"];    To  = T[occ]
        co2  = df[f"{z}_co2"]; c2o = co2[occ]
        rh   = df[f"{z}_rh"]
        mdot = df[f"{z}_mdot_cmd"]
        cap  = MAX_MDOT[z]

        tOk2  = pct((To  >= COOL_SP-2) & (To  <= COOL_SP+2)) if len(To)  else 0.0
        c800o = pct(c2o < CO2_TARGET)                          if len(c2o) else 0.0

        m[z] = dict(
            # temperature
            t1_all  = pct((T  >= COOL_SP-1) & (T  <= COOL_SP+1)),
            t2_all  = pct((T  >= COOL_SP-2) & (T  <= COOL_SP+2)),
            tAbv    = pct(T > COOL_SP),
            tMean   = T.mean(), tMin=T.min(), tMax=T.max(), tStd=T.std(),
            tOk1    = tOk2,   # primary metric is now ±2°C
            tOk2    = tOk2,
            dh      = ((T[T > COOL_SP] - COOL_SP) * TIMESTEP_H).sum(),
            # CO2
            c800    = pct(co2 < CO2_TARGET),
            c1000   = pct(co2 < CO2_LIMIT),
            c800o   = c800o,
            cMean   = co2.mean(), cMax=co2.max(),
            # humidity
            rhOpt   = pct((rh >= RH_OPT_LO) & (rh <= RH_OPT_HI)),
            rhHi    = pct(rh > RH_OPT_HI),
            rhLo    = pct(rh < RH_OPT_LO),
            rhMean  = rh.mean(),
            # airflow
            util    = mdot.mean() / cap * 100,
            sat_pct = pct(mdot >= cap * 0.99),
            zero_pct= pct(mdot <= 0.001),
            meanMdot= mdot.mean(), cap=cap,
            # combined score — use ±2°C as the temperature component
            combined= tOk2 * 0.40 + c800o * 0.35 +
                      pct((rh >= RH_OPT_LO) & (rh <= RH_OPT_HI)) * 0.25,
        )

    # AHU
    sat = df["AHU_SAT_cmd"]; oa = df["AHU_OA_cmd"]
    total_mdot  = sum(df[f"{z}_mdot_cmd"] for z in ZONES)
    safe_total  = total_mdot.replace(0, np.nan)
    oa_frac_pct = (oa / safe_total * 100).clip(0, 100).dropna()
    m["_ahu"] = dict(
        sat_12    = pct((sat >= 11.5) & (sat < 12.5)),
        sat_14    = pct((sat >= 13.5) & (sat < 14.5)),
        sat_other = pct(~(((sat>=11.5)&(sat<12.5)) | ((sat>=13.5)&(sat<14.5)))),
        sat_mean  = sat.mean(), sat_std=sat.std(),
        oa_mean   = oa.mean(),  oa_std=oa.std(),
        oa_frac   = oa_frac_pct,
    )

    # Aggregates
    aT   = pd.concat([df[f"{z}_T"][occ]   for z in ZONES])
    aCO2 = pd.concat([df[f"{z}_co2"][occ] for z in ZONES])
    aRH  = pd.concat([df[f"{z}_rh"]       for z in ZONES])
    aCO2a= pd.concat([df[f"{z}_co2"]      for z in ZONES])
    m["_agg"] = dict(
        t_all  = pct((aT   >= COOL_SP-2) & (aT   <= COOL_SP+2)),  # ±2°C
        c800   = pct(aCO2  < CO2_TARGET),
        c1000  = pct(aCO2a < CO2_LIMIT),
        rh_opt = pct((aRH  >= RH_OPT_LO) & (aRH  <= RH_OPT_HI)),
    )
    return m


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 1  —  PERFORMANCE SCORECARD
# ═════════════════════════════════════════════════════════════════════════════
def fig1_scorecard(m):
    fig = plt.figure(figsize=(22, 16), facecolor=BG, num="Figure 1 — Performance Scorecard")
    fig.patch.set_facecolor(BG)
    fig_title(fig,
              "ME325 — Decentralised HVAC Control · Performance Scorecard",
              "Weighted score: Temperature 40% | CO\u2082 35% | Humidity 25%  (occupied hours)")

    # ── GridSpec: 2 rows (zone cards | KPI strip), 6 cols (5 zones + OVERALL) ──
    gs = gridspec.GridSpec(
        2, 6, figure=fig,
        top=0.90, bottom=0.04,
        left=0.02, right=0.99,
        hspace=0.18, wspace=0.06,
        height_ratios=[1.15, 0.85],
    )

    # ─── Row 0: Zone cards (cols 0-4) + OVERALL (col 5) ──────────────────────
    def draw_zone_card(ax, z, m):
        score = m[z]["combined"]
        gc    = grade_col(score)
        grade = "A" if score>=90 else ("B" if score>=75 else ("C" if score>=60 else "D"))

        ax.set_facecolor(CARD)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        for sp in ["left", "right", "top", "bottom"]:
            ax.spines[sp].set_visible(True)
            ax.spines[sp].set_edgecolor(gc)
            ax.spines[sp].set_linewidth(2.5)

        # Header band
        ax.add_patch(FancyBboxPatch((0, 0.87), 1, 0.13, boxstyle="square,pad=0",
                     facecolor=gc+"44", edgecolor="none", transform=ax.transAxes))
        ax.text(0.5, 0.94, z, ha="center", va="center",
                fontsize=14, fontweight="bold", color=WHITE, transform=ax.transAxes)
        ax.text(0.5, 0.88, ZONE_USE[z], ha="center", va="center",
                fontsize=10, color=DIM, transform=ax.transAxes)

        # Score + Grade (centred in upper-middle area)
        ax.text(0.5, 0.72, f"{score:.0f}%", ha="center", va="center",
                fontsize=36, fontweight="bold", color=gc, transform=ax.transAxes)
        ax.text(0.5, 0.62, f"Grade  {grade}", ha="center", va="center",
                fontsize=16, fontweight="bold", color=gc, transform=ax.transAxes)

        # Divider
        ax.axhline(0.58, xmin=0.05, xmax=0.95, color=BORDER, linewidth=0.8)

        # Metric rows — evenly spaced between 0.54 and 0.18
        rows = [
            ("Temp \u00b12\u00b0C", f"{m[z]['tOk1']:.1f}%",   m[z]['tOk1'], 90, 75),
            ("CO\u2082 <800ppm", f"{m[z]['c800o']:.1f}%",  m[z]['c800o'], 85, 70),
            ("RH 40\u201360%",  f"{m[z]['rhOpt']:.1f}%",  m[z]['rhOpt'], 80, 60),
        ]
        y_positions = [0.49, 0.37, 0.25]
        for (lbl, val_str, val, p, w), y in zip(rows, y_positions):
            c = status_col(val, p, w)
            # Background pill
            ax.add_patch(FancyBboxPatch((0.04, y - 0.045), 0.92, 0.082,
                         boxstyle="round,pad=0.008",
                         facecolor=c+"1A", edgecolor=c+"88", linewidth=0.9,
                         transform=ax.transAxes))
            ax.text(0.10, y, lbl, ha="left", va="center",
                    fontsize=10, color=TEXT, transform=ax.transAxes)
            ax.text(0.90, y, val_str, ha="right", va="center",
                    fontsize=11, fontweight="bold", color=c, transform=ax.transAxes)

        # Degree-hours footnote
        ax.text(0.5, 0.10, f"Degree-hours above SP:",
                ha="center", va="center", fontsize=8.5, color=DIM, transform=ax.transAxes)
        ax.text(0.5, 0.05, f"{m[z]['dh']:.0f} \u00b0C\u00b7h",
                ha="center", va="center", fontsize=9, fontweight="bold",
                color=DIM, transform=ax.transAxes)

    for i, z in enumerate(ZONES):
        ax = fig.add_subplot(gs[0, i])
        draw_zone_card(ax, z, m)

    # OVERALL card (col 5) — same height as zone cards via GridSpec
    overall = np.mean([m[z]["combined"] for z in ZONES])
    oc = grade_col(overall)
    og = "A" if overall>=90 else ("B" if overall>=75 else ("C" if overall>=60 else "D"))
    ov_ax = fig.add_subplot(gs[0, 5])
    ov_ax.set_facecolor("#0B1E09" if oc == GREEN else ("#1E1006" if oc == AMBER else "#1E0806"))
    ov_ax.set_xlim(0, 1); ov_ax.set_ylim(0, 1); ov_ax.axis("off")
    for sp in ["left", "right", "top", "bottom"]:
        ov_ax.spines[sp].set_visible(True)
        ov_ax.spines[sp].set_edgecolor(oc)
        ov_ax.spines[sp].set_linewidth(3)
    ov_ax.add_patch(FancyBboxPatch((0, 0.87), 1, 0.13, boxstyle="square,pad=0",
                    facecolor=oc+"44", edgecolor="none", transform=ov_ax.transAxes))
    ov_ax.text(0.5, 0.935, "OVERALL", ha="center", va="center",
               fontsize=12, fontweight="bold", color=oc, transform=ov_ax.transAxes)
    ov_ax.text(0.5, 0.72,  f"{overall:.0f}%", ha="center", va="center",
               fontsize=36, fontweight="bold", color=oc, transform=ov_ax.transAxes)
    ov_ax.text(0.5, 0.60,  f"Grade  {og}", ha="center", va="center",
               fontsize=16, fontweight="bold", color=oc, transform=ov_ax.transAxes)
    ov_ax.axhline(0.545, xmin=0.08, xmax=0.92, color=BORDER, linewidth=0.8)
    ov_ax.text(0.5, 0.46, "System", ha="center", va="center",
               fontsize=11, color=DIM, transform=ov_ax.transAxes)
    ov_ax.text(0.5, 0.37, "Score",  ha="center", va="center",
               fontsize=11, color=DIM, transform=ov_ax.transAxes)
    ov_ax.text(0.5, 0.22, "5-zone", ha="center", va="center",
               fontsize=10, color=DIM, transform=ov_ax.transAxes)
    ov_ax.text(0.5, 0.12, "weighted avg.", ha="center", va="center",
               fontsize=9, color=DIM, transform=ov_ax.transAxes)

    # ─── Row 1: KPI strip — 4 GridSpec panels ────────────────────────────────
    agg  = m["_agg"]
    kpis = [
        ("Temperature \u00b12\u00b0C",    "All zones, occupied hours",    agg["t_all"],  90, 75),
        ("CO\u2082 below 800 ppm",        "All zones, occupied hours",    agg["c800"],   85, 70),
        ("CO\u2082 below 1000 ppm",       "ASHRAE 62.1 limit, all hours", agg["c1000"],  99, 95),
        ("Humidity 40\u201360 %",         "ASHRAE 55 optimal, all hours", agg["rh_opt"], 80, 60),
    ]
    kpi_specs = [gs[1, 0:2], gs[1, 2:3], gs[1, 3:4], gs[1, 4:6]]

    for (title, subtitle, val, p, w), sspec in zip(kpis, kpi_specs):
        ax  = fig.add_subplot(sspec)
        c   = status_col(val, p, w)
        tag = "PASS" if val >= p else ("WARN" if val >= w else "FAIL")

        ax.set_facecolor(CARD)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        for sp in ["left", "right", "top", "bottom"]:
            ax.spines[sp].set_visible(True)
            ax.spines[sp].set_edgecolor(c)
            ax.spines[sp].set_linewidth(2)

        # Title block
        ax.text(0.5, 0.93, title, ha="center", va="center",
                fontsize=13, fontweight="bold", color=WHITE, transform=ax.transAxes)
        ax.text(0.5, 0.84, subtitle, ha="center", va="center",
                fontsize=10, color=DIM, style="italic", transform=ax.transAxes)

        # Badge
        ax.add_patch(FancyBboxPatch((0.37, 0.71), 0.26, 0.10,
                     boxstyle="round,pad=0.01",
                     facecolor=c+"33", edgecolor=c, linewidth=1.2,
                     transform=ax.transAxes))
        ax.text(0.5, 0.762, tag, ha="center", va="center",
                fontsize=12, fontweight="bold", color=c, transform=ax.transAxes)

        # Big percentage
        ax.text(0.5, 0.52, f"{val:.1f}%", ha="center", va="center",
                fontsize=36, fontweight="bold", color=c, transform=ax.transAxes)

        # Progress bar — track + fill
        ax.add_patch(FancyBboxPatch((0.07, 0.30), 0.86, 0.09,
                     boxstyle="round,pad=0.004",
                     facecolor=BORDER, edgecolor="none", transform=ax.transAxes))
        ax.add_patch(FancyBboxPatch((0.07, 0.30), 0.86 * val / 100, 0.09,
                     boxstyle="round,pad=0.004",
                     facecolor=c, edgecolor="none", alpha=0.90, transform=ax.transAxes))

        # Threshold line
        ax.text(0.5, 0.19, f"Target \u2265{p}%  \u00b7  Warning \u2265{w}%",
                ha="center", va="center",
                fontsize=9.5, color=DIM, style="italic", transform=ax.transAxes)

    # Footer
    fig.text(0.5, 0.005,
             "Grade key:  A \u2265 90%  |  B \u2265 75%  |  C \u2265 60%  |  D < 60%"
             "     \u00b7     Weighting: Temperature 40%  \u00b7  CO\u2082 35%  \u00b7  Humidity 25%",
             ha="center", fontsize=11, color=DIM)
    save(fig, "fig1_scorecard.png")
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 2  —  TEMPERATURE
# ═════════════════════════════════════════════════════════════════════════════
def fig2_temperature(df, m):
    fig = plt.figure(figsize=(20, 15), facecolor=BG, num="Figure 2 — Temperature Results")
    fig_title(fig,
              "ME325 — Temperature Control Results",
              "Cooling setpoint: 24 \u00b0C  |  5-zone commercial office  |  Colombo, Sri Lanka")

    gs = gridspec.GridSpec(2, 2, figure=fig,
                           top=0.90, bottom=0.07, left=0.07, right=0.97,
                           hspace=0.45, wspace=0.35)

    # ── Top-left: ±1°C / ±2°C / Outside stacked bar ─────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(PANEL); spine(ax1)

    labels = [ZONE_USE[z] for z in ZONES]
    t1  = [m[z]["t1_all"]                    for z in ZONES]
    t12 = [m[z]["t2_all"] - m[z]["t1_all"]   for z in ZONES]
    tOu = [100 - m[z]["t2_all"]              for z in ZONES]
    x = np.arange(len(ZONES))
    w = 0.5

    b1 = ax1.bar(x, t1,  w, color=GREEN,   alpha=0.9, label="Within \u00b11 \u00b0C of setpoint")
    b2 = ax1.bar(x, t12, w, bottom=t1, color=AMBER, alpha=0.8, label="Within \u00b12 \u00b0C")
    b3 = ax1.bar(x, tOu, w, bottom=[t1[i]+t12[i] for i in range(5)],
                 color=RED,   alpha=0.7, label="Outside \u00b12 \u00b0C band")

    for b, v in zip(b1, t1):
        ax1.text(b.get_x()+b.get_width()/2, v/2, f"{v:.0f}%",
                 ha="center", va="center", fontsize=13, fontweight="bold", color=WHITE)

    ax1.set_xticks(x); ax1.set_xticklabels(labels, fontsize=11, rotation=15, ha="right")
    ax1.set_ylabel("% of total simulation time", fontsize=13)
    ax1.set_ylim(0, 115)
    ax1.axhline(90, color=GREEN, linewidth=1, linestyle="--", alpha=0.5, label="90% target")
    ax1.set_title("Temperature Band Compliance  (All Hours)", fontsize=15,
                  fontweight="bold", pad=12, loc="left")
    ax1.legend(loc="lower right", fontsize=11)

    # ── Top-right: Occupied-hours ±1°C compliance ────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(PANEL); spine(ax2)

    tOk1 = [m[z]["tOk1"] for z in ZONES]
    cols  = [status_col(v, 90, 75) for v in tOk1]
    bars  = ax2.bar(x, tOk1, w, color=cols, alpha=0.88)

    for b, v, c in zip(bars, tOk1, cols):
        ax2.text(b.get_x()+b.get_width()/2, v+1.5, f"{v:.1f}%",
                 ha="center", va="bottom", fontsize=13, fontweight="bold", color=c)

    ax2.set_xticks(x); ax2.set_xticklabels(labels, fontsize=11, rotation=15, ha="right")
    ax2.set_ylabel("% of occupied timesteps", fontsize=13)
    ax2.set_ylim(0, 115)
    ax2.axhline(90, color=GREEN, linewidth=1, linestyle="--", alpha=0.5, label="90% target")
    ax2.axhline(75, color=AMBER, linewidth=1, linestyle=":", alpha=0.5, label="75% minimum")
    ax2.set_title("Temperature \u00b12 \u00b0C Compliance  (Occupied Hours Mon–Fri 08:00–18:00)",
                  fontsize=15, fontweight="bold", pad=12, loc="left")
    ax2.legend(fontsize=11)

    # ── Bottom: Full-year time-series ─────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, :])
    ax3.set_facecolor(PANEL); spine(ax3)

    x_h = df["sim_hours"].values
    for z, col in ZONE_COLOURS.items():
        y    = df[f"{z}_T"].values
        roll = pd.Series(y).rolling(144, min_periods=1, center=True).mean().values
        ax3.fill_between(x_h, roll, y, alpha=0.07, color=col)
        ax3.plot(x_h, y,    color=col, lw=0.6, alpha=0.4)
        ax3.plot(x_h, roll, color=col, lw=1.8, alpha=0.95, label=ZONE_USE[z])

    ax3.axhline(COOL_SP,    color=RED,  lw=1.5, ls="--", alpha=0.9, label="Setpoint 24 \u00b0C")
    ax3.axhline(COOL_SP+2,  color=AMBER, lw=1.0, ls=":",  alpha=0.6, label="\u00b12 \u00b0C band")
    ax3.axhline(COOL_SP-2,  color=AMBER, lw=1.0, ls=":",  alpha=0.6)
    ax3.fill_between(x_h, COOL_SP-2, COOL_SP+2,
                     alpha=0.06, color=AMBER, label="_nolegend_")

    hours_per_month = [744,672,744,720,744,720,744,744,720,744,720,744]
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    ticks, acc = [0], 0
    for h in hours_per_month:
        acc += h; ticks.append(acc)
    ax3.set_xticks(ticks[:-1])
    ax3.set_xticklabels(month_names, fontsize=12)
    ax3.set_xlim(x_h[0], x_h[-1])
    ax3.set_ylim(19, 32)
    ax3.set_ylabel("Zone Air Temperature (\u00b0C)", fontsize=13)
    ax3.set_title("Full-Year Zone Temperature  (24-hour rolling mean, all 5 zones)",
                  fontsize=15, fontweight="bold", pad=12, loc="left")
    ax3.legend(loc="upper right", fontsize=11, ncol=6)

    save(fig, "fig2_temperature.png")
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 3  —  CO₂ AND HUMIDITY
# ═════════════════════════════════════════════════════════════════════════════
def fig3_co2_rh(df, m):
    fig = plt.figure(figsize=(20, 15), facecolor=BG, num="Figure 3 — CO\u2082 & Humidity Results")
    fig_title(fig,
              "ME325 — Air Quality & Humidity Results",
              "CO\u2082 target: 800 ppm  |  ASHRAE 62.1 limit: 1000 ppm  |  Humidity comfort band: 40\u201360 %")

    gs = gridspec.GridSpec(2, 2, figure=fig,
                           top=0.90, bottom=0.07, left=0.07, right=0.97,
                           hspace=0.45, wspace=0.35)

    labels = [ZONE_USE[z] for z in ZONES]
    x = np.arange(len(ZONES)); w = 0.5

    # ── Top-left: CO₂ stacked bar (all hours) ────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(PANEL); spine(ax1)

    c800  = [m[z]["c800"]               for z in ZONES]
    c_mid = [m[z]["c1000"]-m[z]["c800"] for z in ZONES]
    c_bad = [100-m[z]["c1000"]          for z in ZONES]

    b1 = ax1.bar(x, c800,  w, color=GREEN, alpha=0.9, label="Below 800 ppm (controller target)")
    b2 = ax1.bar(x, c_mid, w, bottom=c800, color=AMBER, alpha=0.8, label="800–1000 ppm")
    b3 = ax1.bar(x, c_bad, w,
                 bottom=[c800[i]+c_mid[i] for i in range(5)],
                 color=RED, alpha=0.7, label="Above 1000 ppm (ASHRAE limit exceeded)")

    for b, v in zip(b1, c800):
        ax1.text(b.get_x()+b.get_width()/2, v/2, f"{v:.0f}%",
                 ha="center", va="center", fontsize=13, fontweight="bold", color=WHITE)

    ax1.set_xticks(x); ax1.set_xticklabels(labels, fontsize=11, rotation=15, ha="right")
    ax1.set_ylabel("% of total simulation time", fontsize=13)
    ax1.set_ylim(0, 115)
    ax1.set_title("CO\u2082 Compliance  (All Hours)", fontsize=15, fontweight="bold", pad=12, loc="left")
    ax1.legend(loc="lower right", fontsize=10)

    # ── Top-right: CO₂ occupied hours ────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(PANEL); spine(ax2)

    c800o = [m[z]["c800o"] for z in ZONES]
    cols  = [status_col(v, 85, 70) for v in c800o]
    bars  = ax2.bar(x, c800o, w, color=cols, alpha=0.88)

    for b, v, c in zip(bars, c800o, cols):
        ax2.text(b.get_x()+b.get_width()/2, v+1.5, f"{v:.1f}%",
                 ha="center", va="bottom", fontsize=13, fontweight="bold", color=c)

    # Mean CO2 scatter
    ax2b = ax2.twinx()
    ax2b.set_facecolor("none")
    cMean = [m[z]["cMean"] for z in ZONES]
    ax2b.plot(x, cMean, "D--", color=BLUE, markersize=10, linewidth=1.5,
              label="Mean CO\u2082 (ppm)", zorder=5)
    ax2b.axhline(CO2_TARGET, color=AMBER, lw=1, ls=":", alpha=0.7)
    ax2b.set_ylabel("Mean CO\u2082 concentration (ppm)", fontsize=12, color=BLUE)
    ax2b.tick_params(axis="y", colors=BLUE)
    ax2b.set_ylim(300, 1100)
    ax2b.legend(loc="upper right", fontsize=10)

    ax2.set_xticks(x); ax2.set_xticklabels(labels, fontsize=11, rotation=15, ha="right")
    ax2.set_ylabel("% of occupied timesteps", fontsize=13)
    ax2.set_ylim(0, 115)
    ax2.axhline(85, color=GREEN, lw=1, ls="--", alpha=0.5, label="85% target")
    ax2.set_title("CO\u2082 Below 800 ppm  (Occupied Hours)", fontsize=15,
                  fontweight="bold", pad=12, loc="left")
    ax2.legend(loc="lower left", fontsize=10)

    # ── Bottom-left: RH stacked bar ───────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor(PANEL); spine(ax3)

    rhOpt = [m[z]["rhOpt"] for z in ZONES]
    rhHi  = [m[z]["rhHi"]  for z in ZONES]
    rhLo  = [m[z]["rhLo"]  for z in ZONES]

    b1 = ax3.bar(x, rhOpt, w, color=GREEN, alpha=0.9, label="40\u201360 % (ASHRAE optimal)")
    b2 = ax3.bar(x, rhHi,  w, bottom=rhOpt, color=RED, alpha=0.8, label="> 60 % (too humid)")
    b3 = ax3.bar(x, rhLo,  w,
                 bottom=[rhOpt[i]+rhHi[i] for i in range(5)],
                 color=BLUE, alpha=0.6, label="< 40 % (too dry)")

    for b, v in zip(b1, rhOpt):
        ax3.text(b.get_x()+b.get_width()/2, v/2, f"{v:.0f}%",
                 ha="center", va="center", fontsize=13, fontweight="bold", color=WHITE)

    ax3.set_xticks(x); ax3.set_xticklabels(labels, fontsize=11, rotation=15, ha="right")
    ax3.set_ylabel("% of total simulation time", fontsize=13)
    ax3.set_ylim(0, 115)
    ax3.set_title("Relative Humidity Band Compliance  (All Hours)", fontsize=15,
                  fontweight="bold", pad=12, loc="left")
    ax3.legend(loc="lower right", fontsize=10)

    # ── Bottom-right: CO₂ full-year time-series ───────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_facecolor(PANEL); spine(ax4)

    x_h = df["sim_hours"].values
    for z, col in ZONE_COLOURS.items():
        y    = df[f"{z}_co2"].values
        roll = pd.Series(y).rolling(144, min_periods=1, center=True).mean().values
        ax4.plot(x_h, roll, color=col, lw=1.8, alpha=0.95, label=ZONE_USE[z])

    ax4.axhline(CO2_TARGET, color=AMBER, lw=1.5, ls="--", alpha=0.8, label="Target 800 ppm")
    ax4.axhline(CO2_LIMIT,  color=RED,   lw=1.5, ls="--", alpha=0.8, label="ASHRAE limit 1000 ppm")

    hours_per_month = [744,672,744,720,744,720,744,744,720,744,720,744]
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    ticks, acc = [0], 0
    for h in hours_per_month:
        acc += h; ticks.append(acc)
    ax4.set_xticks(ticks[:-1]); ax4.set_xticklabels(month_names, fontsize=11)
    ax4.set_xlim(x_h[0], x_h[-1])
    ax4.set_ylabel("CO\u2082 Concentration (ppm)", fontsize=13)
    ax4.set_title("Full-Year CO\u2082 Trend  (24-hr rolling mean)", fontsize=15,
                  fontweight="bold", pad=12, loc="left")
    ax4.legend(fontsize=10, ncol=2)

    save(fig, "fig3_co2_rh.png")
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# FIGURE 4  —  AIRFLOW & AHU
# ═════════════════════════════════════════════════════════════════════════════
def fig4_airflow_ahu(df, m):
    fig = plt.figure(figsize=(20, 14), facecolor=BG, num="Figure 4 — Airflow & AHU")
    fig_title(fig,
              "ME325 — Airflow Utilisation & AHU System Behaviour",
              "VAV terminal utilisation  |  AHU supply air temperature  |  Demand-controlled ventilation")

    gs = gridspec.GridSpec(2, 3, figure=fig,
                           top=0.90, bottom=0.07, left=0.07, right=0.97,
                           hspace=0.48, wspace=0.40)

    labels = [ZONE_USE[z] for z in ZONES]
    x = np.arange(len(ZONES)); w = 0.35

    # ── Top-left: Airflow utilisation bars ───────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor(PANEL); spine(ax1)

    util = [m[z]["util"]     for z in ZONES]
    sat  = [m[z]["sat_pct"]  for z in ZONES]
    cols = [ZONE_COLOURS[z]  for z in ZONES]

    b1 = ax1.bar(x - w/2, util, w, color=cols, alpha=0.88, label="Avg utilisation (%)")
    b2 = ax1.bar(x + w/2, sat,  w, color=RED,  alpha=0.65, label="Saturated (at max flow)")

    for b, v, c in zip(b1, util, cols):
        ax1.text(b.get_x()+b.get_width()/2, v+1.2, f"{v:.0f}%",
                 ha="center", va="bottom", fontsize=12, fontweight="bold", color=c)
    for b, v in zip(b2, sat):
        ax1.text(b.get_x()+b.get_width()/2, v+1.2, f"{v:.0f}%",
                 ha="center", va="bottom", fontsize=10, color=RED)

    ax1.set_xticks(x); ax1.set_xticklabels(labels, fontsize=11, rotation=15, ha="right")
    ax1.set_ylabel("% of simulation time / capacity", fontsize=12)
    ax1.set_ylim(0, 115)
    ax1.set_title("VAV Terminal Utilisation", fontsize=15, fontweight="bold", pad=12, loc="left")
    ax1.legend(fontsize=11)

    # ── Top-middle: AHU SAT distribution ─────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor(PANEL); spine(ax2)

    ahu = m["_ahu"]
    sat_labels = ["12 \u00b0C\n(Humidity override)", "14 \u00b0C\n(Normal cooling)", "Other"]
    sat_vals   = [ahu["sat_12"], ahu["sat_14"], ahu["sat_other"]]
    sat_cols   = [BLUE, GREEN, AMBER]

    b_sat = ax2.bar(sat_labels, sat_vals, color=sat_cols, alpha=0.88, width=0.45)
    for b, v in zip(b_sat, sat_vals):
        ax2.text(b.get_x()+b.get_width()/2, v+1.0, f"{v:.1f}%",
                 ha="center", va="bottom", fontsize=14, fontweight="bold", color=TEXT)

    ax2.set_ylabel("% of simulation time", fontsize=12)
    ax2.set_ylim(0, max(sat_vals)*1.35 + 5)
    ax2.set_title("AHU Supply Air Temp (SAT) Distribution", fontsize=15,
                  fontweight="bold", pad=12, loc="left")
    ax2.text(0.5, 0.94, f"Mean SAT = {ahu['sat_mean']:.1f} \u00b0C  (\u00b1{ahu['sat_std']:.1f} \u00b0C)",
             transform=ax2.transAxes, ha="center", fontsize=11, color=DIM)

    # ── Top-right: OA fraction histogram ─────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor(PANEL); spine(ax3)

    oa_frac = ahu["oa_frac"]
    bins = np.linspace(0, 100, 21)
    counts, edges = np.histogram(oa_frac, bins=bins)
    pcts_oa = counts / len(oa_frac) * 100
    mids = (edges[:-1] + edges[1:]) / 2
    b_oa = ax3.bar(mids, pcts_oa, width=5,
                   color=[GREEN if m >= 15 else RED for m in mids],
                   alpha=0.8, edgecolor=BG, linewidth=0.5)

    ax3.axvline(15, color=AMBER, lw=2.0, ls="--", label="Code minimum 15%")
    ax3.set_xlabel("Outdoor Air Fraction (%)", fontsize=12)
    ax3.set_ylabel("% of timesteps", fontsize=12)
    ax3.set_title("Demand-Controlled Ventilation (OA Fraction)", fontsize=15,
                  fontweight="bold", pad=12, loc="left")
    ax3.legend(fontsize=11)
    ax3.text(0.96, 0.92, f"Mean OA: {oa_frac.mean():.0f}%",
             transform=ax3.transAxes, ha="right", fontsize=11, color=DIM)

    # ── Bottom: Airflow time-series (all zones) ───────────────────────────
    ax4 = fig.add_subplot(gs[1, :])
    ax4.set_facecolor(PANEL); spine(ax4)

    x_h = df["sim_hours"].values
    for z, col in ZONE_COLOURS.items():
        y    = df[f"{z}_mdot_cmd"].values
        roll = pd.Series(y).rolling(144, min_periods=1, center=True).mean().values
        ax4.plot(x_h, roll, color=col, lw=1.8, alpha=0.9, label=ZONE_USE[z])
        # Capacity line
        ax4.axhline(MAX_MDOT[z], color=col, lw=0.7, ls=":", alpha=0.4)

    hours_per_month = [744,672,744,720,744,720,744,744,720,744,720,744]
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    ticks, acc = [0], 0
    for h in hours_per_month:
        acc += h; ticks.append(acc)
    ax4.set_xticks(ticks[:-1]); ax4.set_xticklabels(month_names, fontsize=12)
    ax4.set_xlim(x_h[0], x_h[-1])
    ax4.set_ylabel("Supply Mass Flow Rate (kg/s)", fontsize=13)
    ax4.set_title("Full-Year Airflow Commands per Zone  (24-hr rolling mean  \u00b7  dotted lines = max capacity)",
                  fontsize=15, fontweight="bold", pad=12, loc="left")
    ax4.legend(fontsize=11, ncol=5, loc="upper right")

    save(fig, "fig4_airflow_ahu.png")
    return fig


# ─────────────────────────── MAIN ────────────────────────────────────────────
def main():
    print("\n-- ME325 Results Summary --")
    df  = load(LOG_PATH)
    occ = is_occupied(df)
    print(f"  Occupied timesteps (Mon-Fri 08:00-18:00): {occ.mean()*100:.1f}%")
    print("  Computing metrics...")
    m = compute_metrics(df, occ)

    print("\n  Building figures...")
    f1 = fig1_scorecard(m)
    f2 = fig2_temperature(df, m)
    f3 = fig3_co2_rh(df, m)
    f4 = fig4_airflow_ahu(df, m)

    print("\n  All figures displayed. Close each window to exit.")
    plt.show()


if __name__ == "__main__":
    main()
