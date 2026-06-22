"""Zone 4 — Server Room.

Example of WHY you'd want a separate file per zone: this zone has a 24/7 high
equipment load and a tighter setpoint, so it can override the base logic
(e.g. never let flow drop to zero, enforce a hard upper temperature limit).
Zones 2, 3 and 5 follow the same pattern as zone1.py unless they need overrides.
"""
from controllers.zone_controller import ZoneController


class Zone4Controller(ZoneController):
    def step(self, meas, dt):
        req = super().step(meas, dt)
        # Server room safety floor: always keep some cooling airflow.
        min_mdot = 0.30 * self.cfg["max_mdot"]
        req["mdot"] = max(req["mdot"], min_mdot)
        return req
