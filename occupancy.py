"""IDF-schedule occupancy mirror — with daily random maximum occupancy.

The 'Office Occupancy' Schedule:Compact fraction (defined in the IDF) is left
completely untouched.  Instead, this module overrides the *Number of People*
field via the EnergyPlus 'People → Number of People' actuator.

EnergyPlus internally computes:
    actual_people(t) = today_max  ×  schedule_fraction(t)

So on weekdays between 08:00–18:00 (fraction = 1.0) the full today_max people
are present; outside those hours only 5 % are present; weekends → 0.

Each zone draws a fresh random integer at midnight of every simulation day,
bounded by the per-zone [occ_min, occ_max] caps defined in config.py.

IDF schedule (Office Occupancy, Fraction):
    Weekdays / SummerDesignDay:
        Until 08:00 → 0.05
        Until 18:00 → 1.00
        Until 24:00 → 0.05
    All other days:
        Until 24:00 → 0.00

Zone default caps (from IDF People objects — kept for reference):
    Zone 1  →  IDF default 8   |  caps: [4, 12]
    Zone 2  →  IDF default 4   |  caps: [2,  6]
    Zone 3  →  IDF default 12  |  caps: [3, 20]
    Zone 4  →  IDF default 1   |  caps: [1,  2]
    Zone 5  →  IDF default 5   |  caps: [2,  8]
"""

import random


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
    """Daily-randomised occupancy model for one zone.

    Each simulation day a new random integer is drawn from [occ_min, occ_max].
    That value is written to the EnergyPlus 'People → Number of People'
    actuator by main.py, so EnergyPlus uses it as the peak capacity for the
    day.  The IDF schedule fraction is then multiplied on top.

    Attributes
    ----------
    today_max  : int    this day's random peak headcount (actuator value)
    current    : float  expected people count at the current timestep
                        (= today_max × schedule_fraction)
    occ_min    : int    lower cap for the random draw
    occ_max    : int    upper cap for the random draw
    """

    def __init__(self, occ_min, occ_max):
        self.occ_min = occ_min
        self.occ_max = occ_max
        self.today_max = random.randint(occ_min, occ_max)  # initial draw
        self.current = 0.0
        self._last_day = None   # tracks EnergyPlus day-of-month

    def step(self, hour, day_of_week_ep, day_of_month):
        """Compute and cache the expected people count for this timestep.

        A new today_max is drawn whenever the simulation day changes (i.e. at
        midnight of each new day).

        Parameters
        ----------
        hour           : float  hour of day (0–23.99)
        day_of_week_ep : int    EnergyPlus day-of-week (1=Sun … 7=Sat)
        day_of_month   : int    EnergyPlus day of month (1–31)

        Returns
        -------
        float : expected people count for this timestep
        """
        # Refresh today_max at the start of each new day
        if day_of_month != self._last_day:
            self.today_max = random.randint(self.occ_min, self.occ_max)
            self._last_day = day_of_month

        fraction = _office_occupancy_fraction(hour, day_of_week_ep)
        self.current = self.today_max * fraction
        return self.current


# ---------------------------------------------------------------------------
# Factory — must stay in sync with config.py ZONES list
# ---------------------------------------------------------------------------
def build_occupancy_models(zones_cfg):
    """Return a list of ZoneOccupancy instances, one per zone config dict.

    Parameters
    ----------
    zones_cfg : list[dict]  zone config dicts from config.py
                            Must have 'occ_min' and 'occ_max' keys.
    """
    return [
        ZoneOccupancy(occ_min=z["occ_min"], occ_max=z["occ_max"])
        for z in zones_cfg
    ]
