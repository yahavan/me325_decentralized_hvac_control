"""Central AHU coordinator (lightweight).

Aggregates every zone's request and picks the AHU-level commands:
  * supply-air-temperature setpoint  (drives cooling + dehumidification)
  * outdoor-air mass flow            (drives CO2 dilution / ventilation)
This is the only place that sees all zones at once. Keep it cheap — a rule or
a small convex program — per the project's "lightweight coordinator" intent.
"""
from config import CO2_SETPOINT, OUTDOOR_CO2, SAT_FLOOR


class AHUCoordinator:
    def __init__(self, zones):
        self.zones = zones

    def coordinate(self, requests):
        """requests = list of per-zone dicts from ZoneController.step().
        Returns dict(sat_sp, oa_flow).  >>> replace with your AHU policy <<<
        """
        # SAT: serve the most-demanding (lowest) zone request, clamped to a floor.
        sat = max(SAT_FLOOR, min(r["t_sup_req"] for r in requests))

        # OA: scale ventilation by the worst (highest-CO2) zone.
        co2_max = max(r["co2"] for r in requests)
        tot_mdot = sum(r["mdot"] for r in requests)
        oa_frac = (co2_max - OUTDOOR_CO2) / (CO2_SETPOINT - OUTDOOR_CO2)
        oa_frac = min(1.0, max(0.15, oa_frac))

        return dict(sat_sp=sat, oa_flow=oa_frac * tot_mdot)
