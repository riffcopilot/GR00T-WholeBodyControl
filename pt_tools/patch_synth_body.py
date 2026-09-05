"""Local patch: let the isaac-teleop input path run without Pico body tracking.

Consumer Pico 4 Ultra headsets do not expose XR_BD_body_tracking over WebXR, so
FullBodyTrackerPico never reports a valid joint and the streamer blocks forever in
"waiting for Isaac Teleop body data". PLANNER + VR_3PT only consume SMPL joints
0 (pelvis), 12 (neck), 22/23 (wrists); we synthesize those from the head pose and
the two controller poses and tag the sample `synthetic=True`. POSE mode (full-body
SMPL) is refused on synthetic samples.
"""
import re, sys, pathlib
root = pathlib.Path(sys.argv[1])
ir = root / "gear_sonic/utils/teleop/input_readers.py"
mg = root / "gear_sonic/scripts/pico_manager_thread_server.py"

s = ir.read_text()
if "_synthetic_body_from_head_and_controllers" not in s:
    helper = '''

# ---------------------------------------------------------------------------
# Local patch (Physical Turing): synthetic body for headsets without body tracking
# ---------------------------------------------------------------------------
_SYNTH_PELVIS_DROP = 0.65   # m below the head (OpenXR y-up)
_SYNTH_NECK_DROP = 0.12
_SYNTH_LOGGED: set[str] = set()


def _log_once(key: str, msg: str) -> None:
    if key in _SYNTH_LOGGED:
        return
    _SYNTH_LOGGED.add(key)
    logger.warning(msg)


def _pose7(pose: Any) -> np.ndarray | None:
    """[x,y,z,qx,qy,qz,qw] from a DeviceIO pose wrapper with .is_valid/.pose, else None."""
    if pose is None or not getattr(pose, "is_valid", False):
        return None
    p = pose.pose.position
    o = pose.pose.orientation
    return np.array([p.x, p.y, p.z, o.x, o.y, o.z, o.w], dtype=np.float32)


def _controller_pose7(snapshot: Any) -> np.ndarray | None:
    if snapshot is None:
        return None
    for name in ("grip_pose", "aim_pose"):
        v = _pose7(getattr(snapshot, name, None))
        if v is not None:
            return v
    return None


def _yaw_only_quat_xyzw(q_xyzw: np.ndarray) -> np.ndarray:
    """Keep only the rotation about the vertical (y) axis of a y-up frame."""
    from scipy.spatial.transform import Rotation as _R

    fwd = _R.from_quat(q_xyzw).apply([0.0, 0.0, -1.0])
    fwd[1] = 0.0
    n = float(np.linalg.norm(fwd))
    if n < 1e-3:
        return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
    fwd /= n
    yaw = float(np.arctan2(-fwd[0], -fwd[2]))
    return _R.from_rotvec([0.0, yaw, 0.0]).as_quat().astype(np.float32)


def _synthetic_body_from_head_and_controllers(raw: dict[str, Any]) -> np.ndarray | None:
    """(24, 7) body array with pelvis/neck/head derived from the headset and the
    wrists from the controllers. Returns None until head + both controllers are valid."""
    head = _pose7(raw.get("head"))
    lw = _controller_pose7(raw.get("left_controller"))
    rw = _controller_pose7(raw.get("right_controller"))
    if head is None:
        _log_once("head", "[synthetic body] waiting for a valid head pose")
        return None
    if lw is None or rw is None:
        _log_once("ctrl", "[synthetic body] head OK, waiting for BOTH controller poses (wake the controllers)")
        return None
    yaw_q = _yaw_only_quat_xyzw(head[3:])
    pelvis = np.concatenate([head[:3] - np.array([0.0, _SYNTH_PELVIS_DROP, 0.0], dtype=np.float32), yaw_q])
    neck = np.concatenate([head[:3] - np.array([0.0, _SYNTH_NECK_DROP, 0.0], dtype=np.float32), yaw_q])
    body = np.tile(pelvis, (_NUM_BODY_JOINTS, 1)).astype(np.float32)
    body[12] = neck
    body[15] = head
    body[20] = lw
    body[22] = lw
    body[21] = rw
    body[23] = rw
    _log_once("ok", "[synthetic body] streaming pelvis/neck from head + wrists from controllers (no body tracking)")
    return body
'''
    # insert helper right before the IsaacTeleopReader class
    s = s.replace("\nclass IsaacTeleopReader:", helper + "\n\nclass IsaacTeleopReader:", 1)
    old = '''            body_poses = _body_data_to_24x7(raw.get("full_body"))
            if body_poses is None:
'''
    new = '''            body_poses = _body_data_to_24x7(raw.get("full_body"))
            synthetic = False
            if body_poses is None:
                body_poses = _synthetic_body_from_head_and_controllers(raw)
                synthetic = body_poses is not None
            if body_poses is None:
'''
    assert old in s; s = s.replace(old, new, 1)
    old = '''                "body_poses_np": body_poses,
                "timestamp_realtime": time.time(),
'''
    new = '''                "body_poses_np": body_poses,
                "synthetic": synthetic,
                "timestamp_realtime": time.time(),
'''
    assert old in s; s = s.replace(old, new, 1)
    ir.write_text(s); print("patched", ir)
else:
    print("already patched", ir)

m = mg.read_text()
if "synthetic body: POSE mode refused" not in m:
    old = '''            # Handle mode transitions before running loop
            if new_mode != current_mode:
'''
    new = '''            # Local patch: full-body POSE mode needs real body tracking
            if new_mode == StreamMode.POSE and new_mode != current_mode:
                _s = reader.get_latest()
                if _s is not None and _s.get("synthetic"):
                    print("[Manager] synthetic body: POSE mode refused (no body tracking on this headset)")
                    new_mode = current_mode

            # Handle mode transitions before running loop
            if new_mode != current_mode:
'''
    assert old in m; m = m.replace(old, new, 1)
    mg.write_text(m); print("patched", mg)
else:
    print("already patched", mg)
