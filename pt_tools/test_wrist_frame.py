"""Numeric check: with a big constant grip->hand rotation C, only the body-frame composition tracks world rotations."""
import numpy as np
from scipy.spatial.transform import Rotation as R
rng = np.random.default_rng(0)
C = R.from_euler("xyz", [90, 0, 30], degrees=True)          # grip frame -> hand frame (large, constant)
g1_0 = R.from_euler("xyz", [10, -20, 5], degrees=True)      # robot wrist at calibration
vr_0 = g1_0 * C.inv()                                       # controller reading at calibration (W = G*C)
off_world = g1_0 * vr_0.inv()                               # upstream: left-multiplied offset
off_body = vr_0.inv() * g1_0                                # patch: right-multiplied offset
errs_w, errs_b = [], []
for _ in range(200):
    dR = R.from_rotvec(rng.normal(size=3) * 0.8)            # the operator rotates the hand in the world
    vr = dR * vr_0
    want = dR * g1_0
    errs_w.append((off_world * vr * want.inv()).magnitude())
    errs_b.append((vr * off_body * want.inv()).magnitude())
print(f"world-frame offset (upstream): mean err {np.degrees(np.mean(errs_w)):.1f} deg, max {np.degrees(np.max(errs_w)):.1f} deg")
print(f"body-frame offset (patch):     mean err {np.degrees(np.mean(errs_b)):.2e} deg, max {np.degrees(np.max(errs_b)):.2e} deg")
