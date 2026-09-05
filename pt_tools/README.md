# Physical Turing — SONIC on the Jetson AGX Thor with a consumer Pico 4 Ultra

Local changes to GR00T-WholeBodyControl (commit a0732b6) plus the operational scripts that live in `~` on the Thor.
The full ledger (what was tried, what passed, every gotcha) is `SONIC_SIM_NOTES.md` in this folder.

## Source patches (already applied on this branch)
- `gear_sonic/utils/teleop/input_readers.py` — **synthetic body**: a consumer Pico sends no body-tracking joints over
  WebXR, so pelvis/neck are derived from the head and the wrists from the controller poses (`patch_synth_body.py`);
  root heading locked at engage / VR_3PT click (`patch_root_lock.py`); small filters.
- `gear_sonic/scripts/pico_manager_thread_server.py` — POSE mode refused on synthetic samples; stop combo must be
  held 0.4 s and cannot fire from the press that started the policy (`patch_stop_debounce*.py`); wrist orientation
  calibration composed in the hand frame (`patch_wrist_frame.py`, proven by `test_wrist_frame.py`); optional fixed
  controller→hand constants (`patch_fixed_hand_offset.py`, `SONIC_FIXED_HAND_OFFSET=1`); 1 Hz stick + wrist logs.
- `gear_sonic_deploy/.../dex3_hands.hpp` — Dex3 default gains lowered to kp 0.5 / kd 0.1 (lab rule).
- `gear_sonic/utils/mujoco_sim/unitree_sdk2py_bridge.py` — prints the elastic-band state (headless driving).

## Scripts (copy to `~` on the Thor)
| script | purpose |
|---|---|
| `sonic_build.sh` | build env + `just build` (CUDA 13 / TensorRT 10.13, no `install_deps.sh`) |
| `sonic_sim_all.sh` | whole sim teleop stack: deploy (zmq_manager sim) → MuJoCo on Xvfb :99 → Pico streamer/CloudXR → spring watcher → headset sim panel |
| `sonic_gateC.sh`, `sonic_watchC.sh`, `sonic_drop.sh`, `sonic_sim_view.py`, `sonic_view_start.sh` | pieces of the above |
| `sonic_real.sh` | real robot: preflight (link, no other stack, no sim, `sonic_bus_check.py`) → deploy `real` waits at the Proceed prompt → streamer → CloudXR watchdog |
| `sonic_real_go2.sh` | answer the prompt (**motors engage**, 3 s ramp to the default stand) and guard the hold until the headset combo (90 °C → `O`) |
| `sonic_real_shutdown.sh` | `O` (damping) + everything down; `sonic_real_deploy_only.sh` restarts just the deploy |
| `sonic_bus_check.py`, `sonic_mode_check.py` | is anyone on the Thor publishing rt/lowcmd? which onboard mode is active? |
| `sonic_temp_watch.py` | motor/driver temperatures at 2 Hz (ankle rolls are the thermal limit on the gantry) |
| `sonic_pico_restart.sh`, `sonic_cxr_watchdog.sh` | streamer/CloudXR restart (+ sim panel), idle-signaling watchdog |
| `sonic_stand.py`, `sonic_live.py`, `sonic_tilt.py`, `sonic_pos.py`, `sonic_probe_xr.py`, `wrist_axes.py` | diagnostics |

Operator flow (real robot, gantry): connect headset → stand square, look straight ahead → `sonic_real_go2.sh` →
A+B+X+Y once → left-stick click (hold the controllers like the robot's hands) → VR_3PT. Four buttons held = stop.
