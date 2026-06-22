"""Base decentralised zone controller.

One instance per zone. It sees ONLY its own zone's measurements (that is what
makes the scheme decentralised). Each step it (1) updates its EKF, then
(2) decides the zone's desired supply mass flow and a local SAT request, which
the AHU coordinator later aggregates.
"""
from estimation.ekf import ZoneEKF, default_init


class ZoneController:
    def __init__(self, cfg):
        self.cfg = cfg
        self.zone = cfg["zone"]
        self.cool_sp = cfg["cool_sp"]          # current cooling setpoint (you may adapt online)
        self.heat_sp = cfg["heat_sp"]
        init = default_init()
        self.ekf = ZoneEKF(init["x0"], init["P0"], init["Q"], init["R"])
        self._last_u = dict(mdot=0.0, t_sup=13.0, w_sup=0.008, c_sup=400.0,
                            t_out=30.0, w_out=0.018, c_out=400.0, q_int=0.0,
                            volume=40.0 * 3.0)

    def step(self, meas, dt):
        """meas = dict(T, w, rh, co2). Returns this zone's request to the AHU."""
        # 1) ESTIMATE — update hidden params/occupancy from measurements.
        #    (wrapped so the scaffold runs before you implement the EKF)
        try:
            self.ekf.update([meas["T"], meas["w"], meas["co2"]], self._last_u, dt)
            est = self.ekf.params.tolist()
        except NotImplementedError:
            est = None

        # 2) CONTROL LAW  >>> replace this P-control stub with your PI / MPC <<<
        err = meas["T"] - self.cool_sp
        mdot = min(max(0.0, self.cfg["kp"] * err) * self.cfg["max_mdot"],
                   self.cfg["max_mdot"])
        t_sup_req = 12.0 if meas["rh"] > self.cfg["rh_target"] else 14.0

        self._last_u.update(mdot=mdot, t_sup=t_sup_req)
        return dict(zone=self.zone, mdot=mdot, t_sup_req=t_sup_req,
                    co2=meas["co2"], cool_sp=self.cool_sp, est=est)
