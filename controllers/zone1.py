"""Zone 1 — Open Office.

Standard behaviour, so this file just binds the base controller to Zone 1's
config. Put any Zone-1-specific control logic here by overriding step().
"""
from controllers.zone_controller import ZoneController


class Zone1Controller(ZoneController):
    pass
