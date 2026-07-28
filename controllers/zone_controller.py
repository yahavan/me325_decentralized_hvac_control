"""Base decentralised zone controller — PI with anti-windup + adaptive gains.

One instance per zone. It sees ONLY its own zone's measurements (that is what
makes the scheme decentralised). Each step it (1) updates its EKF, then
(2) runs a discrete PI control law to decide the zone's desired supply mass
flow and a local SAT request, which the AHU coordinator later aggregates.

PI recap
--------
  u(t) = Kp_eff * e(t)  +  Ki_eff * ∫e dt
  where Kp_eff = Kp * kp_mult(hour, weekday)
        Ki_eff = Ki * ki_mult(hour, weekday)

Adaptive gain schedule (weekdays)
----------------------------------
  00:00–07:30  Night        kp × 0.50, ki × 0.40  — low load, slow dynamics
  07:30–09:00  Ramp-up      kp × 1.50, ki × 1.00  — fight occupancy surge
  09:00–17:30  Peak          kp × 1.00, ki × 1.00  — baseline (config values)
  17:30–19:00  Ramp-down    kp × 1.10, ki × 1.00  — slight boost at changeover
  19:00–24:00  After-hours  kp × 0.70, ki × 0.60  — reduced, near-empty zone

Weekends: kp × 0.50, ki × 0.40 throughout (0.05-fraction occupancy all day).

Zone 4 (Server Room) overrides _gain_multiplier() to always return (1.0, 1.0)
because its load is constant 24/7.

Anti-windup
-----------
If the computed u would exceed the actuator limits [0, max_mdot], the
output is clamped AND the integral is *not* updated further in that
direction (conditional integration).
"""
from estimation.ekf import ZoneEKF, default_init


class ZoneController:
    def __init__(self, cfg):
        self.cfg = cfg
        self.zone = cfg["zone"]
        self.cool_sp = cfg["cool_sp"]          # cooling setpoint [°C]
        self.heat_sp = cfg["heat_sp"]
        self.kp = cfg["kp"]                    # proportional gain  [kg/s / °C]
        self.ki = cfg["ki"]                    # integral gain       [kg/s / (°C·s)]

        # PI integrator state — accumulated error × time [°C·s]
        self._integral = 0.0

        # EKF setup
        init = default_init()
        self.ekf = ZoneEKF(init["x0"], init["P0"], init["Q"], init["R"])
        self._last_u = dict(mdot=0.0, t_sup=13.0, w_sup=0.008, c_sup=400.0,
                            t_out=30.0, w_out=0.018, c_out=400.0, q_int=0.0,
                            volume=40.0 * 3.0)

    def _gain_multiplier(self, hour, is_weekday):
        """Return (kp_mult, ki_mult) for the current time of day.

        Subclasses can override to disable or customise the schedule.

        Parameters
        ----------
        hour       : float  0.0 – 23.99, simulation hour of day
        is_weekday : bool   True for Mon–Fri (EnergyPlus dow 2–6)
        """
        if not is_weekday:
            # Weekend: near-zero occupancy all day — use night-level gains.
            return 0.50, 0.40

        if 7.5 <= hour < 9.0:
            # Pre-occupancy ramp: fight the 08:00 step-change heat surge.
            return 1.50, 1.00
        elif 9.0 <= hour < 17.5:
            # Peak occupancy: use the baseline gains from config.
            return 1.00, 1.00
        elif 17.5 <= hour < 19.0:
            # Evening changeover: slight boost while people are leaving.
            return 1.10, 1.00
        elif 19.0 <= hour:
            # After hours: reduced — zone is nearly empty.
            return 0.70, 0.60
        else:
            # Night (00:00–07:30): minimal activity, slow thermal dynamics.
            return 0.50, 0.40

    def step(self, meas, dt, hour=12.0, is_weekday=True):
        """meas = dict(T, w, rh, co2).  dt in seconds.
        hour       : float, simulation hour of day (for gain scheduling).
        is_weekday : bool,  True for Mon–Fri.
        Returns this zone's request dict to the AHU coordinator.
        """
        # 1) ESTIMATE — update hidden params/occupancy from measurements.
        try:
            self.ekf.update([meas["T"], meas["w"], meas["co2"]], self._last_u, dt)
            est = self.ekf.params.tolist()
        except NotImplementedError:
            est = None

        # 2) PI CONTROL LAW with adaptive gain scheduling
        #    Error: positive when zone is too warm (needs more cooling airflow).
        err = meas["T"] - self.cool_sp

        # Compute effective gains for this timestep.
        kp_mult, ki_mult = self._gain_multiplier(hour, is_weekday)
        kp_eff = self.kp * kp_mult
        ki_eff = self.ki * ki_mult

        # --- Conditional integration (anti-windup) ---
        # Tentatively update the integrator.
        integral_candidate = self._integral + err * dt

        # Compute raw PI output with the candidate integral.
        u_raw = kp_eff * err + ki_eff * integral_candidate

        # Clamp output to actuator range [0, max_mdot].
        mdot = min(max(0.0, u_raw), self.cfg["max_mdot"])

        # Only accept the integral update if the output was NOT saturated,
        # or if saturation is in the opposite direction to the integrator growth.
        # (This is the "clamping" anti-windup strategy.)
        saturated_high = u_raw >= self.cfg["max_mdot"] and err > 0
        saturated_low  = u_raw <= 0.0               and err < 0
        if not (saturated_high or saturated_low):
            self._integral = integral_candidate
        # else: leave self._integral unchanged — freeze accumulation at the limit.

        # 3) SAT request: proportional — slides from 14°C (dry) to 12°C (humid)
        #    based on how far RH is from target. Avoids the bang-bang switching
        #    that causes saw-tooth oscillation in humidity.
        #    At rh_target      → 13°C (neutral)
        #    At rh_target + 5% → 12°C (max dehumidification)
        #    At rh_target - 5% → 14°C (back off)
        rh_err = meas["rh"] - self.cfg["rh_target"]   # +ve = too humid
        t_sup_req = max(12.0, min(14.0, 13.0 - 0.2 * rh_err))

        self._last_u.update(mdot=mdot, t_sup=t_sup_req)
        return dict(zone=self.zone, mdot=mdot, t_sup_req=t_sup_req,
                    co2=meas["co2"], cool_sp=self.cool_sp, est=est)
