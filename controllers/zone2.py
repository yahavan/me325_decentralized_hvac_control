"""Zone 2 — Private Offices.

Standard behaviour; binds the base controller to Zone 2's config. Add any
Zone-2-specific logic by overriding step() (see zone4.py for the pattern).
"""
from controllers.zone_controller import ZoneController


class Zone2Controller(ZoneController):
    pass
