"""Base decentralised zone controller — PI + EKF.

One instance per zone. It sees ONLY its own zone's measurements (that is what
makes the scheme decentralised). Each step it:
  1) Updates its EKF to estimate hidden params (C_T, U, occupancy heat gain …)
  2) Runs a PI control law for temperature → desired supply mass flow
  3) Returns a request dict to the AHU coordinator

PI control eliminates the steady-state offset that a pure P-controller has:
  mdot = clamp(kp·e + ki·∫e·dt,  0,  max_mdot)
"""
from estimation.ekf import ZoneEKF, default_init


class ZoneController:
    def __init__(self, cfg):
        self.cfg      = cfg
        self.zone     = cfg["zone"]
        self.cool_sp  = cfg["cool_sp"]    # cooling setpoint (°C)
        self.heat_sp  = cfg["heat_sp"]

        # PI gains — kp from config, ki tuned conservatively
        self.kp = cfg["kp"]
        self.ki = cfg.get("ki", self.kp * 0.05)   # default ki = 5% of kp

        # Integrator state
        self._integral = 0.0
        self._integral_limit = cfg["max_mdot"] / max(self.ki, 1e-9)   # anti-windup

        # EKF
        init      = default_init()
        self.ekf  = ZoneEKF(init["x0"], init["P0"], init["Q"], init["R"])
        self._last_u = dict(
            mdot=0.0, t_sup=13.0, w_sup=0.008, c_sup=400.0,
            t_out=30.0, w_out=0.018, c_out=400.0, q_int=0.0,
            volume=40.0 * 3.0
        )

    def step(self, meas, dt):
        """meas = dict(T, w, rh, co2). Returns this zone's request to the AHU."""

        # ── 1) ESTIMATE — update hidden params from measurements ──────
        try:
            self.ekf.update(
                [meas["T"], meas["w"], meas["co2"]],
                self._last_u,
                dt
            )
            est = self.ekf.params.tolist()
            # Use EKF estimate of q_occ to anticipate load
            q_occ_est = self.ekf.estimated_occupancy_heat
        except Exception:
            est       = None
            q_occ_est = 0.0

        # ── 2) PI CONTROL LAW ─────────────────────────────────────────
        err = meas["T"] - self.cool_sp

        # Integrate error (anti-windup: clamp integral)
        self._integral += err * dt
        self._integral = max(-self._integral_limit,
                             min(self._integral_limit, self._integral))

        # PI output
        u_pi = self.kp * err + self.ki * self._integral

        # Clamp to [0, max_mdot]
        mdot = min(max(0.0, u_pi), 1.0) * self.cfg["max_mdot"]

        # Choose supply air temperature request based on humidity
        t_sup_req = 12.0 if meas["rh"] > self.cfg["rh_target"] else 14.0

        # Reset integrator if zone is well within comfort band (±0.3°C)
        if abs(err) < 0.3:
            self._integral *= 0.95   # slow bleed-off, avoids integrator wind-up

        self._last_u.update(mdot=mdot, t_sup=t_sup_req)

        return dict(
            zone      = self.zone,
            mdot      = mdot,
            t_sup_req = t_sup_req,
            co2       = meas["co2"],
            cool_sp   = self.cool_sp,
            est       = est,
            q_occ_est = q_occ_est,
        )
