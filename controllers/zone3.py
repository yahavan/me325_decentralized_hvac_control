"""Zone 3 — Conference Room.

Standard behaviour; binds the base controller to Zone 3's config. This zone has
the highest occupancy/CO2 swing, so it is a likely candidate for a CO2-aware
override later (e.g. boost flow ahead of meetings) — add it by overriding step().
"""
from controllers.zone_controller import ZoneController


class Zone3Controller(ZoneController):
    pass
