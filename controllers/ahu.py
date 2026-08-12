"""Central AHU coordinator (lightweight).

Aggregates every zone's request and picks the AHU-level commands:
  * supply-air-temperature setpoint  (drives cooling + dehumidification)
  * outdoor-air mass flow            (drives CO2 dilution / ventilation)
This is the only place that sees all zones at once. Keep it cheap — a rule or
a small convex program — per the project's "lightweight coordinator" intent.
"""
from config import CO2_SETPOINT, OUTDOOR_CO2, SAT_FLOOR

COOL_SP  = 24.0   # °C — zone cooling setpoint (mirrors config per-zone value)
SAT_HIGH = 14.0   # °C — warmest allowed SAT (standard cooling mode)


class AHUCoordinator:
    def __init__(self, zones):
        self.zones = zones

    def coordinate(self, requests):
        """requests = list of per-zone dicts from ZoneController.step().
        Returns dict(sat_sp, oa_flow).
        """
        # ── Step 1: humidity-driven SAT from zone controllers ──────────────
        # Take the lowest SAT request (most demanding zone), clamped to floor.
        sat_humidity = max(SAT_FLOOR, min(r["t_sup_req"] for r in requests))

        # ── Step 2: temperature-based SAT reset ────────────────────────────
        # If the average zone temperature is already BELOW setpoint, the AHU
        # is over-cooling.  We progressively raise the SAT toward SAT_HIGH so
        # supply air is warmer and zones can recover toward 24 °C.
        #
        #   mean_T >= COOL_SP          → no adjustment (zones are at/above SP)
        #   mean_T = COOL_SP - 0.5 °C → raise SAT by 1 °C
        #   mean_T = COOL_SP - 1.0 °C → raise SAT by 2 °C  (max reset)
        #
        # The reset is capped at +2 °C so it never completely overrides a
        # genuine humidity demand.
        mean_T = sum(r.get("T_zone", COOL_SP) for r in requests) / len(requests)
        under_cool = max(0.0, COOL_SP - mean_T)           # how many °C below SP
        sat_reset  = min(2.0, under_cool * 2.0)           # up to +2 °C correction

        sat = min(SAT_HIGH, sat_humidity + sat_reset)
        sat = max(SAT_FLOOR, sat)                          # always respect the floor

        # ── Step 3: outdoor air (demand-controlled ventilation) ────────────
        co2_max  = max(r["co2"] for r in requests)
        tot_mdot = sum(r["mdot"] for r in requests)
        oa_frac  = (co2_max - OUTDOOR_CO2) / (CO2_SETPOINT - OUTDOOR_CO2)
        oa_frac  = min(1.0, max(0.15, oa_frac))

        return dict(sat_sp=sat, oa_flow=oa_frac * tot_mdot)
