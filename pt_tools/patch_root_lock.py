"""Local patch 3: the synthetic root's heading is LOCKED, not the head's heading.

The operator's pelvis does not turn when their head turns. Without a pelvis tracker we take the head heading
once — at engage (A+B+X+Y) and again at every left-stick click into VR_3PT — and hold it. Rule for the operator:
face the robot squarely when you press/click. Root position keeps its slow low-pass (stepping/leaning).
Also logs the robot-vs-controller wrist orientations at calibration so a bad hand pose at the click is visible.
"""
import sys, pathlib, re
root = pathlib.Path(sys.argv[1])
ir = root / "gear_sonic/utils/teleop/input_readers.py"
mg = root / "gear_sonic/scripts/pico_manager_thread_server.py"

s = ir.read_text()
if "def reset_synthetic_root" not in s:
    old = "_SYNTH_FILTER: dict = {}\n"
    new = old + '''

def reset_synthetic_root() -> None:
    """Re-capture the root heading from the current head heading on the next frame (engage / VR_3PT click)."""
    _SYNTH_FILTER.pop("root_q_locked", None)
    _SYNTH_FILTER.pop("root_q", None)
    logger.warning("[synthetic body] root heading will be re-captured from the head on the next frame")
'''
    assert old in s; s = s.replace(old, new, 1)
    old = '    root_q = _ema_q("root_q", yaw_q, _SYNTH_ROOT_TAU)\n'
    new = '''    if f.get("root_q_locked") is None:
        f["root_q_locked"] = yaw_q.copy()
    root_q = f["root_q_locked"]
'''
    assert old in s; s = s.replace(old, new, 1)
    ir.write_text(s); print("patched reader (root lock)")
else:
    print("reader already patched")

m = mg.read_text()
if "reset_synthetic_root" not in m:
    # 1) engage: OFF -> PLANNER happens right where CALIB_FULL is triggered (calibrate_now on the start combo)
    old = "                    sample = reader.get_latest()\n                    if sample is not None:\n                        three_point.calibrate_now(sample[\"body_poses_np\"])\n"
    assert m.count(old) == 1, m.count(old)
    new = "                    if sample_is_synthetic(reader):\n                        input_readers.reset_synthetic_root()\n" + old
    m = m.replace(old, new, 1)
    # 2) every entry into VR_3PT
    old = "                elif new_mode == StreamMode.PLANNER_VR_3PT:\n                    # Recalibrate VR tracking against the robot's actual current pose\n"
    assert m.count(old) == 1
    new = "                elif new_mode == StreamMode.PLANNER_VR_3PT:\n                    if sample_is_synthetic(reader):\n                        input_readers.reset_synthetic_root()\n                    # Recalibrate VR tracking against the robot's actual current pose\n"
    m = m.replace(old, new, 1)
    # helper
    old = "def get_abxy_buttons(reader=None):\n"
    new = '''def sample_is_synthetic(reader) -> bool:
    try:
        s = reader.get_latest()
        return bool(s is not None and s.get("synthetic"))
    except Exception:
        return False


''' + old
    assert m.count(old) == 1; m = m.replace(old, new, 1)
    # 3) log orientations at calibration capture
    old = "        # Compute orientation offsets: calibrated = rot_offset * neck_corrected\n"
    new = '''        _e = lambda r: [int(v) for v in r.as_euler("xyz", degrees=True)]
        print(f"[{self.log_prefix}] calib orientations (robot frame, deg xyz): "
              f"robot L {_e(g1_lwrist_rot)} R {_e(g1_rwrist_rot)} | operator L {_e(lwrist_rot_corrected)} R {_e(rwrist_rot_corrected)}", flush=True)
''' + old
    assert m.count(old) == 1; m = m.replace(old, new, 1)
    mg.write_text(m); print("patched manager (root reset hooks + calib orientation log)")
else:
    print("manager already patched")
