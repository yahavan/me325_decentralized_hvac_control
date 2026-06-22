"""Per-zone Extended Kalman Filter.

Augmented state (one zone):
    x = [ T, w, c,                      <- measured states
          C_T, U, C_w, k, q_occ ]       <- hidden parameters / gains to estimate

Measurements:
    z = [ T, w (or RH), c ]

Parameters get random-walk dynamics (theta_dot = 0 + process noise) so the
filter can slowly track them. Fill in predict()/update() from your three
sub-model equations (see the thermal / moisture / CO2 balances).
"""
import numpy as np


class ZoneEKF:
    def __init__(self, x0, P0, Q, R):
        self.x = np.asarray(x0, dtype=float)   # augmented state estimate
        self.P = np.asarray(P0, dtype=float)   # estimate covariance
        self.Q = np.asarray(Q, dtype=float)    # process noise covariance
        self.R = np.asarray(R, dtype=float)    # measurement noise covariance

    # ----- prediction step -------------------------------------------------
    def predict(self, u, dt):
        """u = dict of known inputs this step:
        mdot, t_sup, w_sup, c_sup, t_out, w_out, c_out, q_int, volume.
        >>> implement x_pred = f(x, u, dt) and F = df/dx, then:
            self.P = F @ self.P @ F.T + self.Q
        """
        # x_pred = self._f(self.x, u, dt)
        # F = self._jacobian_f(self.x, u, dt)
        # self.x = x_pred
        # self.P = F @ self.P @ F.T + self.Q
        raise NotImplementedError("fill in f() and its Jacobian")

    # ----- measurement update ---------------------------------------------
    def update(self, z, u, dt):
        """z = measurement vector [T, w, c]. Returns current param estimates."""
        # self.predict(u, dt)
        # H = self._jacobian_h(self.x)            # d(measurement)/d(state)
        # y = z - self._h(self.x)                 # innovation
        # S = H @ self.P @ H.T + self.R
        # K = self.P @ H.T @ np.linalg.inv(S)     # Kalman gain
        # self.x = self.x + K @ y
        # self.P = (np.eye(len(self.x)) - K @ H) @ self.P
        raise NotImplementedError("fill in h(), Jacobians, gain update")

    # ----- accessors -------------------------------------------------------
    @property
    def params(self):
        """[C_T, U, C_w, k, q_occ] once update() is implemented."""
        return self.x[3:].copy()


def default_init():
    """Reasonable starting guesses/covariances for a 40 m2 zone. Tune these."""
    x0 = [24.0, 0.010, 500.0,      # T, w, c
          3.0e5, 50.0, 2.0e4, 0.01, 0.0]   # C_T, U, C_w, k, q_occ
    P0 = np.diag([0.5, 1e-6, 100.0, 1e9, 100.0, 1e6, 1e-3, 1.0])
    Q  = np.diag([0.01, 1e-9, 1.0, 1e6, 1.0, 1e3, 1e-5, 0.1])
    R  = np.diag([0.1, 1e-7, 25.0])        # sensor noise: T, w, CO2
    return dict(x0=x0, P0=P0, Q=Q, R=R)
