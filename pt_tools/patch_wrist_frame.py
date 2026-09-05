"""Local patch 2: wrist orientation from a controller must be composed in the HAND frame.

SONIC calibrates R_off = R_g1 * R_vr^-1 and applies calibrated = R_off * R_vr (a world-frame correction).
That is right when the tracked wrist frame is anatomically the hand (BD skeleton, R_off ~ small yaw), but a
controller grip frame is rigidly attached to the hand with a LARGE constant rotation C: W = G * C. Then a
world rotation dR of the controller (G = dR * G0) must give dR * W0, which only the body-frame composition
calibrated = R_vr * (R_vr0^-1 * R_g1_0) delivers; the world-frame version maps a controller pitch into a
wrist roll/yaw -> the "forearm turned the wrong way and dangling" seen on the robot 2026-09-04.
Enabled only for synthetic samples (real body tracking keeps upstream behaviour).
Also: pelvis/neck from a low-passed head (2 s / 0.5 s) so head motion doesn't swing the arms, and a 60 ms
EMA on the controller poses to take the jitter out without perceptible lag.
"""
import sys, pathlib
root = pathlib.Path(sys.argv[1])
mg = root / "gear_sonic/scripts/pico_manager_thread_server.py"
ir = root / "gear_sonic/utils/teleop/input_readers.py"

m = mg.read_text()
if "body_frame_wrist_offset" not in m:
    old = """        # Compute orientation offsets: calibrated = rot_offset * neck_corrected
        self._calibration_lwrist_rot_offset = g1_lwrist_rot * lwrist_rot_corrected.inv()
        self._calibration_rwrist_rot_offset = g1_rwrist_rot * rwrist_rot_corrected.inv()
"""
    new = """        # Compute orientation offsets: calibrated = rot_offset * neck_corrected
        self._calibration_lwrist_rot_offset = g1_lwrist_rot * lwrist_rot_corrected.inv()
        self._calibration_rwrist_rot_offset = g1_rwrist_rot * rwrist_rot_corrected.inv()
        # Local patch: hand-frame (right-multiplied) offsets for controller-derived wrists
        self._calibration_lwrist_rot_offset_body = lwrist_rot_corrected.inv() * g1_lwrist_rot
        self._calibration_rwrist_rot_offset_body = rwrist_rot_corrected.inv() * g1_rwrist_rot
"""
    assert old in m; m = m.replace(old, new, 1)
    old = """        # Wrist orientations: rot_offset * (neck_inv * current)
        if self._calibration_lwrist_rot_offset is not None:
            lw_corrected = calib_inv_rot * sRot.from_quat(vr_3pt_pose[0, 3:], scalar_first=True)
            calibrated[0, 3:] = (self._calibration_lwrist_rot_offset * lw_corrected).as_quat(
                scalar_first=True
            )
        if self._calibration_rwrist_rot_offset is not None:
            rw_corrected = calib_inv_rot * sRot.from_quat(vr_3pt_pose[1, 3:], scalar_first=True)
            calibrated[1, 3:] = (self._calibration_rwrist_rot_offset * rw_corrected).as_quat(
                scalar_first=True
            )
"""
    new = """        # Wrist orientations: rot_offset * (neck_inv * current)
        # Local patch: with body_frame_wrist_offset (controller-derived wrists) use current * offset_body
        if self._calibration_lwrist_rot_offset is not None:
            lw_corrected = calib_inv_rot * sRot.from_quat(vr_3pt_pose[0, 3:], scalar_first=True)
            if getattr(self, "body_frame_wrist_offset", False) and getattr(self, "_calibration_lwrist_rot_offset_body", None) is not None:
                lw_cal = lw_corrected * self._calibration_lwrist_rot_offset_body
            else:
                lw_cal = self._calibration_lwrist_rot_offset * lw_corrected
            calibrated[0, 3:] = lw_cal.as_quat(scalar_first=True)
        if self._calibration_rwrist_rot_offset is not None:
            rw_corrected = calib_inv_rot * sRot.from_quat(vr_3pt_pose[1, 3:], scalar_first=True)
            if getattr(self, "body_frame_wrist_offset", False) and getattr(self, "_calibration_rwrist_rot_offset_body", None) is not None:
                rw_cal = rw_corrected * self._calibration_rwrist_rot_offset_body
            else:
                rw_cal = self._calibration_rwrist_rot_offset * rw_corrected
            calibrated[1, 3:] = rw_cal.as_quat(scalar_first=True)
"""
    assert old in m; m = m.replace(old, new, 1)
    old = """                if sample is not None:
                    print("[PlannerLoop] Sending VR 3-point pose as target")
                    vr_3pt_pose = self.three_point.process_smpl_pose(sample["body_poses_np"])
"""
    new = """                if sample is not None:
                    self.three_point.body_frame_wrist_offset = bool(sample.get("synthetic", False))
                    vr_3pt_pose = self.three_point.process_smpl_pose(sample["body_poses_np"])
"""
    assert old in m; m = m.replace(old, new, 1)
    import re
    m2, n = re.subn(r"(def _clear_calibration\(self\):.*?self\._calibration_rwrist_rot_offset = None\n)",
                    r"\1        self._calibration_lwrist_rot_offset_body = None\n        self._calibration_rwrist_rot_offset_body = None\n", m, count=1, flags=re.S)
    assert n == 1; m = m2
    mg.write_text(m); print("patched manager (wrist frame)")
else:
    print("manager already patched")

s = ir.read_text()
if "_SYNTH_FILTER" not in s:
    old = """    yaw_q = _yaw_only_quat_xyzw(head[3:])
    pelvis = np.concatenate([head[:3] - np.array([0.0, _SYNTH_PELVIS_DROP, 0.0], dtype=np.float32), yaw_q])
    neck = np.concatenate([head[:3] - np.array([0.0, _SYNTH_NECK_DROP, 0.0], dtype=np.float32), yaw_q])
"""
    new = """    # Low-pass the root (pelvis) hard and the neck lightly: the operator's head is NOT their pelvis.
    # Controllers get a short EMA against tracking jitter.
    from scipy.spatial.transform import Rotation as _R, Slerp as _Slerp
    now = time.monotonic()
    f = _SYNTH_FILTER
    dt = 0.0 if f.get("t") is None else max(1e-3, now - f["t"]); f["t"] = now
    def _ema(key, val, tau):
        prev = f.get(key)
        if prev is None or tau <= 0: f[key] = val; return val
        a = 1.0 - np.exp(-dt / tau)
        out = prev + a * (val - prev); f[key] = out; return out
    def _ema_q(key, q, tau):
        prev = f.get(key)
        if prev is None or tau <= 0: f[key] = q; return q
        a = float(1.0 - np.exp(-dt / tau))
        r = _Slerp([0.0, 1.0], _R.from_quat([prev, q]))(a).as_quat().astype(np.float32); f[key] = r; return r
    yaw_q = _yaw_only_quat_xyzw(head[3:])
    root_pos = _ema("root_pos", head[:3].astype(np.float32), _SYNTH_ROOT_TAU)
    root_q = _ema_q("root_q", yaw_q, _SYNTH_ROOT_TAU)
    neck_q = _ema_q("neck_q", yaw_q, _SYNTH_NECK_TAU)
    lw = np.concatenate([_ema("lw_p", lw[:3], _SYNTH_CTRL_TAU), _ema_q("lw_q", lw[3:], _SYNTH_CTRL_TAU)])
    rw = np.concatenate([_ema("rw_p", rw[:3], _SYNTH_CTRL_TAU), _ema_q("rw_q", rw[3:], _SYNTH_CTRL_TAU)])
    pelvis = np.concatenate([root_pos - np.array([0.0, _SYNTH_PELVIS_DROP, 0.0], dtype=np.float32), root_q])
    neck = np.concatenate([head[:3] - np.array([0.0, _SYNTH_NECK_DROP, 0.0], dtype=np.float32), neck_q])
"""
    assert old in s; s = s.replace(old, new, 1)
    s = s.replace("_SYNTH_NECK_DROP = 0.12\n", "_SYNTH_NECK_DROP = 0.12\n_SYNTH_ROOT_TAU = 2.0    # s, pelvis position + yaw follow the head slowly\n_SYNTH_NECK_TAU = 0.5    # s\n_SYNTH_CTRL_TAU = 0.06   # s, controller jitter filter\n_SYNTH_FILTER: dict = {}\n", 1)
    ir.write_text(s); print("patched reader (filters)")
else:
    print("reader already patched")
