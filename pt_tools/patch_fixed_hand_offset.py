"""Local patch 4: fixed controller->hand orientation constants (what the AGILE/IsaacTeleop retargeter does) instead
of re-learning them from the operator's hand pose at every left-stick click; and a fixed (non-head-following) torso.

The constants are derived from the 2026-09-04 18:01 click where the operator mimicked the robot's hands well:
  robot L [63, 66, 20]  R [-81, 68, -33]   (FK of measured q, robot frame, euler xyz deg)
  operator L [135, -10, 63]  R [-134, -11, -61]   (controller-derived, after neck correction)
C = R_operator^-1 * R_robot per hand (hand-frame). Position offsets are still calibrated at every click.
"""
import sys, pathlib, numpy as np
from scipy.spatial.transform import Rotation as R
root = pathlib.Path(sys.argv[1])
mg = root / "gear_sonic/scripts/pico_manager_thread_server.py"
ir = root / "gear_sonic/utils/teleop/input_readers.py"
CL = (R.from_euler("xyz", [135, -10, 63], degrees=True).inv() * R.from_euler("xyz", [63, 66, 20], degrees=True)).as_quat(scalar_first=True)
CR = (R.from_euler("xyz", [-134, -11, -61], degrees=True).inv() * R.from_euler("xyz", [-81, 68, -33], degrees=True)).as_quat(scalar_first=True)
print("C_L wxyz", np.round(CL, 4), "C_R wxyz", np.round(CR, 4))
print("C_L as euler", np.round(R.from_quat(CL, scalar_first=True).as_euler("xyz", degrees=True), 1),
      "C_R as euler", np.round(R.from_quat(CR, scalar_first=True).as_euler("xyz", degrees=True), 1))

m = mg.read_text()
if "FIXED_HAND_OFFSET_L" not in m:
    old = """        # Local patch: hand-frame (right-multiplied) offsets for controller-derived wrists
        self._calibration_lwrist_rot_offset_body = lwrist_rot_corrected.inv() * g1_lwrist_rot
        self._calibration_rwrist_rot_offset_body = rwrist_rot_corrected.inv() * g1_rwrist_rot
"""
    new = f"""        # Local patch: hand-frame (right-multiplied) offsets for controller-derived wrists.
        # FIXED constants (measured 2026-09-04 with the operator mimicking the robot) unless
        # SONIC_LEARN_HAND_OFFSET=1, in which case they are re-learned from the operator's hand pose at this click.
        if os.environ.get("SONIC_LEARN_HAND_OFFSET") == "1":
            self._calibration_lwrist_rot_offset_body = lwrist_rot_corrected.inv() * g1_lwrist_rot
            self._calibration_rwrist_rot_offset_body = rwrist_rot_corrected.inv() * g1_rwrist_rot
            print(f"[{{self.log_prefix}}] hand offsets LEARNED from this click")
        else:
            self._calibration_lwrist_rot_offset_body = sRot.from_quat(FIXED_HAND_OFFSET_L, scalar_first=True)
            self._calibration_rwrist_rot_offset_body = sRot.from_quat(FIXED_HAND_OFFSET_R, scalar_first=True)
            print(f"[{{self.log_prefix}}] hand offsets FIXED (controller->hand constants)")
"""
    assert m.count(old) == 1; m = m.replace(old, new, 1)
    old = "class LocomotionMode(IntEnum):"
    new = f"""# Local patch: controller grip -> G1 wrist constant rotations (hand frame, wxyz), see patch_fixed_hand_offset.py
FIXED_HAND_OFFSET_L = [{', '.join(f'{v:.6f}' for v in CL)}]
FIXED_HAND_OFFSET_R = [{', '.join(f'{v:.6f}' for v in CR)}]


class LocomotionMode(IntEnum):"""
    assert m.count(old) == 1; m = m.replace(old, new, 1)
    mg.write_text(m); print("patched manager (fixed hand offsets)")
else:
    print("manager already patched")

s = ir.read_text()
if "_SYNTH_TORSO_FOLLOWS_HEAD" not in s:
    old = "    neck_q = _ema_q(\"neck_q\", yaw_q, _SYNTH_NECK_TAU)\n"
    new = "    neck_q = _ema_q(\"neck_q\", yaw_q, _SYNTH_NECK_TAU) if _SYNTH_TORSO_FOLLOWS_HEAD else root_q\n"
    assert old in s; s = s.replace(old, new, 1)
    s = s.replace("_SYNTH_FILTER: dict = {}\n", "_SYNTH_TORSO_FOLLOWS_HEAD = False   # True: torso turns with the head; False: torso stays on the locked heading\n_SYNTH_FILTER: dict = {}\n", 1)
    ir.write_text(s); print("patched reader (fixed torso)")
else:
    print("reader already patched")
