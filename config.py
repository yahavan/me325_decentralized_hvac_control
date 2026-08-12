"""Per-zone configuration. One dict per zone; the driver builds a controller
from each. Keep all zone-specific numbers here so the controller code stays generic.
"""

RHO_AIR = 1.2  # kg/m3, converts terminal max flow (m3/s) to a kg/s ceiling

# Terminal max AIR flow (m3/s) matches the fixed values in the IDF.
# Python writes mass flow (kg/s) directly to each terminal; clamp to [0, max_mdot].
ZONES = [
    # occ_min / occ_max: daily random occupancy caps written to the EnergyPlus
    # 'People → Number of People' actuator.  The IDF schedule fraction is still
    # applied on top, so actual_people = today_max × schedule_fraction.
    dict(zone="Zone 1", terminal="Zone 1 Air Terminal", use="Open Office",
         max_flow_m3s=0.50, cool_sp=24.0, heat_sp=18.0, rh_target=55.0, kp=0.18, ki=0.00008,
         occ_min=4,  occ_max=12),   # IDF default 8
    dict(zone="Zone 2", terminal="Zone 2 Air Terminal", use="Private Offices",
         max_flow_m3s=0.35, cool_sp=24.0, heat_sp=18.0, rh_target=55.0, kp=0.18, ki=0.00008,
         occ_min=2,  occ_max=6),    # IDF default 4
    dict(zone="Zone 3", terminal="Zone 3 Air Terminal", use="Conference Room",
         max_flow_m3s=0.55, cool_sp=24.0, heat_sp=18.0, rh_target=55.0, kp=0.22, ki=0.0001,
         occ_min=3,  occ_max=20),   # IDF default 12
    dict(zone="Zone 4", terminal="Zone 4 Air Terminal", use="Server Room",
         max_flow_m3s=0.60, cool_sp=24.0, heat_sp=18.0, rh_target=50.0, kp=0.25, ki=0.00012,
         occ_min=1,  occ_max=2),    # IDF default 1
    dict(zone="Zone 5", terminal="Zone 5 Air Terminal", use="Reception",
         max_flow_m3s=0.35, cool_sp=24.0, heat_sp=18.0, rh_target=55.0, kp=0.18, ki=0.00008,
         occ_min=2,  occ_max=8),    # IDF default 5
]

for _z in ZONES:
    _z["max_mdot"] = _z["max_flow_m3s"] * RHO_AIR

CO2_SETPOINT = 800.0     # ppm, central coordinator target
OUTDOOR_CO2 = 400.0      # ppm
SAT_FLOOR = 10.0         # degC, lowest allowed AHU supply-air temperature
