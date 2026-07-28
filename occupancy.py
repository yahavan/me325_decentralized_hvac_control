"""IDF-schedule occupancy mirror — for logging only.

This module does NOT write to any EnergyPlus actuator. It simply replicates
the 'Office Occupancy' Schedule:Compact defined in the IDF so that the
control_log.csv can record the expected occupancy count each timestep.

EnergyPlus drives the actual heat/CO2 gains from its own schedule internally.

IDF schedule (Office Occupancy, Fraction):
    Weekdays / SummerDesignDay:
        Until 08:00 → 0.05
        Until 18:00 → 1.00
        Until 24:00 → 0.05
    All other days:
        Until 24:00 → 0.00

Zone max people (from IDF People objects, method=People, number=N):
    Zone 1  →  8
    Zone 2  →  4
    Zone 3  → 12
    Zone 4  →  1
    Zone 5  →  5
"""


def _office_occupancy_fraction(hour, day_of_week_ep):
    """Return the Office Occupancy schedule fraction for a given time.

    Parameters
    ----------
    hour              : float  0.0 – 23.99, simulation hour of day
    day_of_week_ep    : int    EnergyPlus convention: 1=Sunday, 2=Monday,
                               3=Tuesday, 4=Wednesday, 5=Thursday,
                               6=Friday, 7=Saturday
    """
    # EnergyPlus weekdays: Mon(2) – Fri(6); weekend: Sun(1), Sat(7)
    is_weekday = 2 <= day_of_week_ep <= 6

    if not is_weekday:
        return 0.0

    if hour < 8.0:
        return 0.05
    elif hour < 18.0:
        return 1.00
    else:
        return 0.05


class ZoneOccupancy:
    """Read-only mirror of the IDF People schedule for one zone.

    Attributes
    ----------
    current    : float  people count computed at the last call to step()
    max_people : int    peak people count from the IDF People object
    """

    def __init__(self, max_people):
        self.max_people = max_people
        self.current = 0.0

    def step(self, hour, day_of_week_ep):
        """Compute and cache the expected people count for this timestep.

        Parameters
        ----------
        hour           : float  hour of day (0–23.99)
        day_of_week_ep : int    EnergyPlus day-of-week (1=Sun … 7=Sat)

        Returns
        -------
        float : people count (fraction × max_people)
        """
        fraction = _office_occupancy_fraction(hour, day_of_week_ep)
        self.current = self.max_people * fraction
        return self.current


# ---------------------------------------------------------------------------
# Zone definitions — must stay in sync with the IDF People objects
# ---------------------------------------------------------------------------
_IDF_MAX_PEOPLE = {
    "Zone 1": 8,
    "Zone 2": 4,
    "Zone 3": 12,
    "Zone 4": 1,
    "Zone 5": 5,
}


def build_occupancy_models(zones_cfg):
    """Return a list of ZoneOccupancy instances, one per zone config dict.

    Parameters
    ----------
    zones_cfg : list[dict]  zone config dicts from config.py (must have 'zone' key)
    """
    models = []
    for z in zones_cfg:
        zone_name = z["zone"]
        max_p = _IDF_MAX_PEOPLE.get(zone_name, 0)
        models.append(ZoneOccupancy(max_people=max_p))
    return models
