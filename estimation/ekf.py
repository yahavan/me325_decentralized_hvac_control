"""Per-zone Extended Kalman Filter — IMPLEMENTED.

Augmented state (one zone):
    x = [ T, w, c,                      <- measured states
          C_T, U, C_w, k, q_occ ]       <- hidden parameters / gains to estimate

Measurements:
    z = [ T, w (or RH), c ]

Parameters get random-walk dynamics (theta_dot = 0 + process noise) so the
filter can slowly track them as occupancy or building properties change.

Physics (same ODEs as simulate.py):
  dT/dt = (mdot·cp·(T_sup - T) + U·(T_out - T) + q_int + q_occ) / C_T
  dw/dt = (mdot·(w_sup - w) + k·occ) / C_w
  dc/dt = (mdot·(c_sup - c) + G_occ) / (V·rho)
"""
import numpy as np

CP_AIR  = 1006.0    # J/(kg·K)
RHO_AIR = 1.2       # kg/m³


class ZoneEKF:
    def __init__(self, x0, P0, Q, R):
        self.x = np.asarray(x0, dtype=float)   # augmented state estimate
        self.P = np.asarray(P0, dtype=float)   # estimate covariance
        self.Q = np.asarray(Q,  dtype=float)   # process noise covariance
        self.R = np.asarray(R,  dtype=float)   # measurement noise covariance

    # ── Internal: nonlinear dynamics f(x, u, dt) ──────────────────
    def _f(self, x, u, dt):
        """Propagate state one step using Euler integration of the zone ODEs."""
        T, w, c = x[0], x[1], x[2]
        C_T, U, C_w, k, q_occ = x[3], x[4], x[5], x[6], x[7]

        # Protect against non-physical parameter estimates
        C_T  = max(C_T,  1e3)
        U    = max(U,    1.0)
        C_w  = max(C_w,  1e2)
        k    = max(k,    0.0)
        q_occ = max(q_occ, 0.0)

        mdot   = u.get("mdot",   0.0)
        t_sup  = u.get("t_sup",  13.0)
        w_sup  = u.get("w_sup",  0.008)
        c_sup  = u.get("c_sup",  400.0)
        t_out  = u.get("t_out",  31.0)
        q_int  = u.get("q_int",  500.0)
        volume = u.get("volume", 120.0)   # m³

        # Thermal ODE
        dT = (mdot * CP_AIR * (t_sup - T) + U * (t_out - T) + q_int + q_occ) / C_T * dt

        # Moisture ODE
        dw = (mdot * (w_sup - w) + k) / C_w * dt

        # CO₂ ODE
        G_occ  = q_occ / 300.0 * 5e-6   # rough: scale CO₂ generation with q_occ
        mass_z = RHO_AIR * volume
        dc = (mdot * (c_sup - c) + G_occ * 1e6) / mass_z * dt

        # Hidden params: random-walk (stay constant ± noise)
        x_new = np.array([
            T + dT,
            max(0.005, w + dw),
            max(400.0, c + dc),
            C_T, U, C_w, k, q_occ          # params unchanged (noise added by Q)
        ])
        return x_new

    # ── Internal: Jacobian of f w.r.t. x (numerical) ──────────────
    def _jacobian_f(self, x, u, dt, eps=1e-4):
        n  = len(x)
        F  = np.zeros((n, n))
        f0 = self._f(x, u, dt)
        for i in range(n):
            xp = x.copy(); xp[i] += eps
            F[:, i] = (self._f(xp, u, dt) - f0) / eps
        return F

    # ── Internal: observation model h(x) ──────────────────────────
    def _h(self, x):
        """We observe T, w, CO₂ directly."""
        return x[:3].copy()

    # ── Internal: Jacobian of h (simple: identity on first 3 states) ─
    def _jacobian_h(self, x):
        H = np.zeros((3, len(x)))
        H[0, 0] = 1.0   # dT_meas/dT
        H[1, 1] = 1.0   # dw_meas/dw
        H[2, 2] = 1.0   # dc_meas/dc
        return H

    # ── Prediction step ───────────────────────────────────────────
    def predict(self, u, dt):
        F      = self._jacobian_f(self.x, u, dt)
        self.x = self._f(self.x, u, dt)
        self.P = F @ self.P @ F.T + self.Q

    # ── Measurement update ────────────────────────────────────────
    def update(self, z, u, dt):
        """z = [T_measured, w_measured, co2_measured]. Updates state + params."""
        self.predict(u, dt)

        z  = np.asarray(z, dtype=float)
        H  = self._jacobian_h(self.x)
        y  = z - self._h(self.x)              # innovation
        S  = H @ self.P @ H.T + self.R        # innovation covariance
        K  = self.P @ H.T @ np.linalg.inv(S) # Kalman gain
        self.x = self.x + K @ y
        self.P = (np.eye(len(self.x)) - K @ H) @ self.P

        # Clamp parameters to physical bounds after update
        self.x[3] = max(self.x[3], 1e3)    # C_T > 0
        self.x[4] = max(self.x[4], 1.0)    # U > 0
        self.x[5] = max(self.x[5], 1e2)    # C_w > 0
        self.x[6] = max(self.x[6], 0.0)    # k >= 0
        self.x[7] = max(self.x[7], 0.0)    # q_occ >= 0

    # ── Accessors ─────────────────────────────────────────────────
    @property
    def params(self):
        """[C_T, U, C_w, k, q_occ] — the estimated hidden parameters."""
        return self.x[3:].copy()

    @property
    def estimated_occupancy_heat(self):
        """Estimated occupancy heat gain (W) — proxy for number of people."""
        return float(self.x[7])


def default_init():
    """Reasonable starting guesses/covariances for a 40 m² zone. Tune these."""
    x0 = [24.0, 0.010, 500.0,              # T, w, c — initial measured states
          3.0e5, 50.0, 2.0e4, 0.01, 0.0]  # C_T, U, C_w, k, q_occ — initial param guesses
    P0 = np.diag([0.5, 1e-6, 100.0,
                  1e9, 100.0, 1e6, 1e-3, 1.0])
    Q  = np.diag([0.01, 1e-9, 1.0,
                  1e6,  1.0,  1e3, 1e-5,  0.1])   # param drift noise
    R  = np.diag([0.1, 1e-7, 25.0])               # sensor noise: T, w, CO₂
    return dict(x0=x0, P0=P0, Q=Q, R=R)
