# SONIC (GR00T-WholeBodyControl) on the Thor — sim spike ledger

Started 2026-09-02. Goal: prove NVIDIA's SONIC whole-body controller runs on our Jetson AGX Thor
and balances/walks in MuJoCo before any real-robot or Seer work. Repo: NVlabs/GR00T-WholeBodyControl
(commit a0732b6), cloned to `~/GR00T-WholeBodyControl`. Nothing under the isaac container, the
capture agent, teleop_node_dev, or the system TensorRT was touched.

## Result so far

| Gate | Status | Evidence |
|---|---|---|
| A. TensorRT build + policy balances | PASS 2026-09-02 | all 3 engines built on TRT 10.13.3 / CUDA 13.0; spring released (printed); 30 s stand: tilt 2.9 deg, joint vel ~0.01 rad/s, 50 Hz loop, policy 0.2 ms |
| B. Planner loads + keyboard walk | PASS 2026-09-02 | `ENTER` -> planner initialized; `2` + `W` -> "Replanning mode WALK", visible gait, tilt max 7.4 deg; `R` halts to a clean stand |
| C. Pico teleop in sim | PASS 2026-09-03 | headset A+B+X+Y engage → stand → A+B gait WALK → left stick drives `Replanning with mode: WALK, movement [-1,0,0]`, visible gait; left-stick click → VR_3PT, 1290 3-point sends, arms follow the controllers (synthetic body); loop 7 ms @ 50 Hz, stream delay 0 ms |
| D. Sim episode export -> Seer ingest | not started | |
| E. On-robot (gantry) balance + VR_3PT arms | PASS 2026-09-04 | see "On-robot spike"; walking not attempted |

Versions: JetPack 7.1 (L4T R38.4), TensorRT 10.13.3.9+cuda13.0 (NOT the doc's Jetson pin 10.7 —
works anyway), CUDA toolkit 13.0.48, onnxruntime 1.16.3 aarch64 (/opt/onnxruntime), just 1.43.0,
uv 0.12.9, sim venv Python 3.10 with mujoco 3.12.0 + torch 2.14.0+cu130 (cuda available).

## Deviations from the upstream install (do these again on a fresh clone)

- Did NOT run `gear_sonic_deploy/scripts/install_deps.sh`: when `nvcc` is not on PATH it
  apt-installs CUDA 12.x toolkits, which is wrong on a CUDA 13 Jetson. Installed its list by hand:
  `build-essential clang cmake ninja-build git-lfs pkg-config patchelf zlib1g-dev libyaml-cpp-dev
  libeigen3-dev libmsgpack-dev libzmq3-dev cppzmq-dev nlohmann-json3-dev libgtest-dev`
  (package is `cppzmq-dev` on 24.04, the script's `cppzmq` does not exist), onnxruntime tgz to
  /opt/onnxruntime + ld.so.conf.d entry, `just` binary to /usr/local/bin.
- Build env: `~/sonic_build.sh` (PATH+=/usr/local/cuda/bin, CUDA_HOME, onnxruntime_DIR,
  TensorRT_ROOT=/usr). `just build` in gear_sonic_deploy, ~3 min. CMake reports
  "missing components: nvparsers" — expected, TRT 10 removed it.
- `install_scripts/install_mujoco_sim.sh` fails at the last step (unitree_sdk2_python needs
  cyclonedds). Fix: `CYCLONEDDS_HOME=~/cyclonedds-install uv pip install -e
  external_dependencies/unitree_sdk2_python` inside `.venv_sim` (the cyclonedds build from the
  xr_teleoperate setup is reused).
- Models: `uv run --python 3.12 --with huggingface_hub python download_from_hf.py` (release
  policy + 774 MB planner ONNX). First deploy run builds `*.trt` engines next to the ONNX files
  (~2 min for the planner); later runs reuse them.
- Local patch (harmless): `gear_sonic/utils/mujoco_sim/unitree_sdk2py_bridge.py` prints
  `ElasticBand enable (viewer): ...` when `9` is pressed in the MuJoCo window, so the release is
  visible in the sim log when driving headless.
- Upstream bug: `ENABLE_ELASTIC_BAND: False` in the wbc yaml crashes the sim
  (`'DefaultEnv' object has no attribute 'elastic_band'`). Keep it True and release with `9`.
  The yaml is back to stock; `g1_29dof_sonic_model12.yaml.orig` is the pristine copy.

## Headless operation (everything over ssh, no monitor, no headset)

- Virtual display `:99` (Xvfb 1600x1000, GLX) + x11vnc on localhost:5999 (password `sonic99`,
  loopback only — the ssh tunnel is the real access control). Start/restart both and the sim with
  `~/sonic_sim_start.sh`; the full gate-A sequence is `SIMDISP=:99 SIMVGL=1 ~/sonic_gateA.sh`.
- **Render on the GPU, not llvmpipe.** Plain Xvfb gives software GL: the sim burned 3+ cores and
  VNC was unusably laggy. Fix = VirtualGL 3.1.3 (arm64 .deb from GitHub, installed to
  /opt/VirtualGL): launch the sim as `vglrun -d egl python gear_sonic/scripts/run_sim_loop.py`
  on `:99` → renderer "NVIDIA Tegra NVIDIA Thor/PCIe", sim ~90% of one core, GPU ~6%.
  (`SIMVGL=1` in `sonic_gateA.sh` does exactly this.)
- Dead end, for the record: the GDM Xorg on `:0` IS GPU-accelerated and `xrandr --fb 1600x1000`
  enlarges it (done, harmless; `~/.Xauth-gdm` is a copy of its cookie), but with no monitor
  connected GLFW's primary monitor is NULL and MuJoCo's compiled `_simulate` module asserts in
  `glfwGetVideoMode` — not patchable from Python. Would need an xorg.conf ConnectedMonitor/EDID
  hack; VirtualGL on Xvfb avoids touching the Thor's X config.
- Watch it from the Mac: `ssh -N -L 5999:localhost:5999 thor` then open `vnc://localhost:5999`
  (Screen Sharing, password `sonic99`). The MuJoCo window is the top-left 1066x666 of the display.
  Tailnet path is direct (~16 ms), so remaining lag is VNC encoding, not the network.
- tmux sessions on the Thor: `sonic-deploy` (the C++ controller, keyboard input goes here:
  `]` start, `ENTER` planner mode, `1/2/3` gait, `WASD` move, `R` halt, `O` stop+exit) and
  `sonic-sim` (MuJoCo). The `9` drop-key must reach the MuJoCo window:
  `DISPLAY=:99 xdotool windowfocus --sync $(xdotool search --name MuJoCo | head -1); xdotool key 9`.
- Screenshots: `DISPLAY=:99 import -window root shot.png` (imagemagick) → `~/sonic_shots/`.
- Numeric state without the viewer: the deploy publishes msgpack on ZMQ tcp://:5557 topic
  `g1_debug` at 50 Hz (`base_quat`, `body_q`, `body_dq`, ...). `~/sonic_stand.py` prints tilt
  stats; `~/sonic_live.py` proves the loop is alive. `base_trans_measured` is a constant
  placeholder in sim — do not use it for displacement.
- Restarting the sim while the deploy is active makes the deploy exit ("Lost LowState data
  connection" → safety stop). Order is always: deploy up (answer Y, wait for Init Done) → sim up →
  `]` → `9`. Engines are cached so a deploy restart is ~20 s.
- Other worlds must be down: the sim's DDS is on `lo` domain 0 only, but the GPU is shared.

## Next

- Gate C: `bash install_scripts/install_pico.sh` (.venv_teleop) then either
  `--input-source isaac-teleop` (in-process CloudXR, H.264, port 48322 — stop the AGILE kit's
  CloudXR first) or the XRoboToolkit APK on the Pico. Engage A+B+X+Y, VR_3PT via Left Stick Click.
- Gate D: `run_data_exporter.py` against the sim with image publishing → LeRobot v2.1 → Seer
  `npm run validate:episode` / branch ingest.
- Not yet exercised: reference-motion playback (`T`), the `sonic_v1_1` / low-latency policies.

## Gate C — Pico over CloudXR into the sim (2026-09-03, lab session)

Status: **headset walking verified** (A+B+X+Y → CALIB_FULL → PLANNER → deploy CONTROL → spring released → stand;
A+B → WALK; left stick → planner movement, robot walks in MuJoCo). VR_3PT verified too: left-stick click → `[ZMQManager] VR 3-point control enabled`, arms follow the
controllers under the synthetic-body patch (operator: "looks good"). One-shot bring-up: `~/sonic_sim_all.sh`.
Headset panel video lags at times (CloudXR video over Wi-Fi: ping Thor→Pico avg 86 ms / max 108 ms while
streaming, signal -53 dBm) — the control path is unaffected (stick/arm response felt immediate).
Gotcha: the four-button combo also fires A+B (next gait) and X+Y (previous gait), so the gait always lands back
on Idle after engaging — press A+B alone to pick a gait before the stick does anything. Same combo = stop.

- `.venv_teleop` via `SKIP_SIM_AND_UNITREE=1 bash install_scripts/install_pico.sh` (isaacteleop 1.3.132rc1,
  CloudXR 6.2.0 runtime downloaded to host `~/.cloudxr`, Quest3 profile — correct for a Pico WebXR client).
  **numpy must stay <2** in this venv (pinocchio is numpy-1 ABI); do not install cupy-cuda13x there (it
  drags numpy 2 in).
- Bring-up: `~/sonic_gateC.sh` (deploy `--input-type zmq_manager sim` → sim on :99 → streamer
  `pico_manager_thread_server.py --manager --input-source isaac-teleop` → watcher `~/sonic_watchC.sh` that
  presses `9` 3 s after the deploy logs "transitioning to CONTROL state"). Streamer-only restart:
  `~/sonic_pico_restart.sh` (CloudXR cert is reused, no re-accept on the headset).
  Headset: `https://192.168.88.247:48322` (cert) → `nvidia.github.io/IsaacTeleop/client/release-1.3.x/`,
  IP 192.168.88.247, H.264, Connect.
- **The headset is a consumer Pico 4 Ultra: zero body-tracking joints over WebXR** (enterprise feature).
  Stock streamer blocks forever in "waiting for Isaac Teleop body data" and never reads the buttons.
  Local patch (`~/patch_synth_body.py`): `input_readers.py` synthesizes the (24,7) body — pelvis/neck from
  the head pose (yaw only), wrists 20-23 from the controller grip/aim poses — and tags samples
  `synthetic=True`; the manager refuses POSE mode on synthetic samples. PLANNER + VR_3PT only use joints
  0/12/22/23 so this is all they need; ankle trackers are irrelevant on this headset.
- Local patch (`~/patch_stop_debounce.py`): the A+B+X+Y **stop** must be held 0.4 s (start stays instant).
  A stop kills the deploy (sim: exits; real robot: motors drop) — a glitchy edge must not do that.
- Headless headset view: `~/sonic_sim_view.py` (tmux `sonic-view`) is a second OpenXR app on the running
  CloudXR runtime (the AGILE Televiz trick) that screen-grabs the MuJoCo window on :99 with mss at 30 fps
  and shows it as a lazy-locked quad layer; uses torch CUDA tensors (not CuPy). The SONIC streamer itself
  renders nothing — the headset view is empty/passthrough by design.
- **Session drops:** CloudXR's signaling handler died ("SignalingRequest: Endpoint unresponsive. Message
  handler will now close", streamsdk log) ~2 min after a runtime start with no client attached; every later
  connect was proxied to the dead handler and the client gave up after exactly 30 s. Symptom on the Pico:
  connects, black, disconnects after 30 s. Fix = restart the streamer (runtime comes with it). Root cause
  not yet known — watch `~/.cloudxr/logs/cxr_streamsdk.*.log` for that line.
- Real-robot prerequisites (not started): G1 on the gantry, slack, powered; the LiveKit `teleop_node`
  (someone else's, `-m teleop_node --adapter g1_manip`) must be stopped — it commands lowcmd; AGILE/GR00T
  worlds down (they are); `deploy.sh --input-type zmq_manager real` auto-picks the 192.168.123.x interface.

## Real robot — prep done 2026-09-04, not yet run

Coordination (from the LiveKit teleop-node agent, verified where possible): its `teleop_node` is dead and does not
auto-restart; only one stack may publish `rt/lowcmd`, and neither stack's preflight recognises the other, so
**the bus check is the rule**: `~/sonic_bus_check.py` (rt/lowcmd + rt/dex3/*/cmd must be 0 msgs for 3 s).

What the deploy does on the real G1 (read from `g1_deploy_onnx_ref.cpp`):
- `deploy.sh --input-type zmq_manager real` auto-picks the 192.168.123.x interface (enP2p1s0).
- It handles the motion switcher itself: `CheckMode` → `ReleaseMode` loop until no mode is active (the robot boots
  in `ai` mode; `SelectMode("normal")` is 7002 on this firmware — not needed).
- **Answering the "Proceed" prompt ENGAGES THE MOTORS**: input/control/command-writer threads start immediately,
  INIT ramps all 29 joints from their current angles to `default_angles` with full body gains over 3 s, then
  WAIT_FOR_CONTROL holds that pose (hands close during the ramp, open at "Init Done"). The headset's A+B+X+Y only
  switches to CONTROL (policy). So the gantry/slack condition applies at the prompt, not at the headset.
- Stop (`O`, four-button hold, or exit) sends a damping command: kp 0, kd 8 on every joint — the robot goes soft,
  it does not hold. On the gantry that is fine; free-standing it is a fall.
- Dex3 hands are commanded (close/open at init, IK targets in VR_3PT). Local patch: driver defaults lowered
  1.5 → **0.5 kp / 0.1 kd** (lab rule after the kp-100 grinding incident); rebuilt 2026-09-04 15:55. Raise toward
  Unitree's example 1.5 only if grasp is too weak.
- `/tmp/relax_all.py` (tv env python) limps every joint if something holds a pose it shouldn't.

Procedure: robot on the gantry, slack, feet near the floor, powered on, remote in someone's hand →
`~/sonic_real.sh` (preflight: link carrier, no other stack, no sim, bus quiet → deploy waits at the prompt,
streamer up) → review the deploy pane (interface, mode release, "G1 type") → `~/sonic_real_go.sh` (Y → 3 s ramp →
"Init Done", robot holding the default stand) → headset: Connect → calibration pose → A+B+X+Y (policy balances) →
VR_3PT arms only on the first session. Stop: four-button hold / `O` / remote L2+B.

### On-robot spike — PASS 2026-09-04 (gantry, arms only)

Attempt 1 (16:10): prompt answered with the feet carrying part of the weight → rigid INIT hold chattered the
ankle rolls (2×STIFFNESS_5020) against the floor: left ankle roll **driver 110 °C** (winding 53, torque -2 Nm) within
~2 min; `[HighTemp]` warning (deploy threshold 90, hysteresis 85, it never cuts motors). Stopped with `O`; the reading
fell to 58 °C in 25 s → driver heating from chatter, not a bad motor.
Attempt 2 (16:17): operator pressed the combo before the deploy was listening — the manager sends `start` once at its
OFF→PLANNER flip, so the press was lost; guard released after 90 s. Rule: **no button until "press"**; a stale
manager needs a streamer restart (`PICO_LOG=~/sonic_pico_real.log ~/sonic_pico_restart.sh`).
Attempt 3 (16:23): gantry carrying the weight, feet touching → `~/sonic_real_go2.sh` (Y → Init Done 16:23:21) →
combo 8 s later → CONTROL 16:23:29, planner IDLE. Robot balanced on its own: tilt ~2°, 50 Hz, policy 0.18 ms,
LowState age 1 ms, stream delay 0. Ankle-roll driver settled 55→67 °C. Left-stick click → VR_3PT: 1264 arm frames,
arms follow the controllers (dq up to 2 rad/s, base stays level, max driver 57 °C, no motorstate errors).
Tools: `~/sonic_temp_watch.py` (tmux sonic-temps → ~/sonic_temps.log), tmux `sonic-guard` presses `O` at ≥90 °C,
`~/sonic_real_deploy_only.sh` restarts just the deploy to the prompt.
Not yet done on the robot: gait/walking, hands under load, free-standing (off gantry), long sessions.
Operator feedback (2026-09-04 session): teleop feels good and MUCH more sensitive than the AGILE kit, with a slight
occasional lag (matches the Wi-Fi jitter seen on the headset link). Forearm fault: **one forearm turned the wrong way and
dangled down** in VR_3PT — wrist motors were healthy at the time (motorstate 0, tau <0.3 Nm, q within ±0.35 rad), so it
is the orientation mapping of the synthetic body (controller grip frame ≠ BD wrist frame), not hardware. The LiveKit
stack hit the same thing (controller→hand anatomical ~90° offset, see teleop-node notes). Fix candidates: capture a
per-wrist orientation offset at the left-stick CALIB (operator's arms match the robot's at that moment) or hard-code
the grip→BD-wrist rotation in `_synthetic_body_from_head_and_controllers`.
Session ended 16:3x with the left-stick click (arms back to planner) then `~/sonic_real_shutdown.sh` (O → damping;
streamer/guard/watchers down; bus quiet). The onboard motion-switcher mode stays RELEASED after a SONIC session —
the robot has no controller until a power cycle restores `ai`.

### Post-session fixes 2026-09-04 (patched, NOT yet verified in sim/robot)
- **Forearm bug root cause (proven numerically, `~/test_wrist_frame.py`)**: SONIC calibrates the wrist orientation offset
  as a world-frame correction (`calibrated = R_off * R_vr`, `R_off = R_g1 * R_vr^-1`). A controller grip frame is rigidly
  attached to the hand with a LARGE constant rotation, and under that composition a world rotation of the hand maps
  wrongly (mean 80°, up to 180° error in the test) — a controller pitch became a wrist roll/yaw → the forearm turned
  and dangled. Fix (`~/patch_wrist_frame.py`): for synthetic samples compose in the hand frame,
  `calibrated = R_vr * (R_vr0^-1 * R_g1_0)` (exact in the test). Real body-tracking keeps upstream behaviour.
- Synthetic body now low-passes the root (pelvis position + yaw, 2 s) and neck (0.5 s) so head motion no longer swings
  the arms, and EMA-filters the controllers (60 ms) against tracking jitter (the "super sensitive" feel).
- Verify in sim first: `~/sonic_sim_all.sh`, engage, left-stick click, rotate a hand about each axis and check the
  robot's wrist follows the same axis. Then robot.

### Headset link hardening 2026-09-04 (evening, sim verification of the wrist fix pending)
- **Headset Wi-Fi is the weak hop**: Thor→router 1.7 ms; Thor→Pico min 5 / avg 146 / max 509 ms (power-save + poor
  link). Client-side session closes ("Terminated ended intentionally", "Close called") and the client page's
  "still need to accept the certificate" both trace to this — the page's cert probe times out. Move the Pico near the
  AP or give it a dedicated 5 GHz router before blaming the stack.
- **Same-origin client**: local patch in `gear_sonic/utils/teleop/isaac_teleop_client.py` passes `host_client=True`
  to `CloudXRLauncher` → the IsaacTeleop web client is served at `https://192.168.88.247:48322/client/` (downloaded
  once to `~/.cloudxr/static-client`). One URL, one cert accept, no cross-origin probe.
- **Sim panel must be restarted with the runtime** (it is a second OpenXR client; a stale one silently shows
  nothing): `~/sonic_pico_restart.sh` now restarts tmux `sonic-view` when present.
- **CloudXR idle signaling death** ("SignalingRequest: Endpoint unresponsive") recurs ~80–130 s after a runtime start
  with no client; seen once mid-session too (harmless then). `~/sonic_cxr_watchdog.sh` (tmux `sonic-cxrwd`, started
  by `sonic_sim_all.sh` / `sonic_real.sh`) restarts the streamer when that line appears and no headset is connected.
- Restart script kill loop anchored (`^python gear_sonic/scripts/pico_manager…`, excludes `$$`/`$PPID`) — the
  unanchored `pgrep -f isaacteleop` matched the calling ssh shell twice today.

### Robot session 2 — 2026-09-04 17:46 (gantry, arms): wrist fix works, heading + hand-pose calibration still off
- Engage → CONTROL → left-stick → VR_3PT, no drama (guarded go, thermal guard). Ended with the left-stick click then
  `~/sonic_real_shutdown.sh`. Right ankle roll driver reached 79 °C by the end (~6 min) — the ankle rolls are the
  thermal limit of gantry sessions; keep sessions short or watch `~/sonic_temps.log`.
- Operator: "the lower wrist problem is fixed" (hand-frame composition works — the forearm no longer dangles), BUT
  (a) with hands straight forward both robot arms pointed 30–45° to the RIGHT, and (b) the right hand needed a 90°
  outward twist for the robot's palm to face inward.
  (a) = the synthetic root heading followed the head (2 s low-pass): looking toward the robot/monitor rotates the whole
  arm frame. Patch (`~/patch_root_lock.py`): root heading is captured ONCE at engage and again at every left-stick
  click (`reset_synthetic_root`) — operator rule: **face the robot squarely when you press/click**.
  (b) = hand orientation at the click ≠ robot's hand orientation (the click calibration assumes they match). Now
  logged at every calibration (`calib orientations (robot frame)` line: robot vs operator wrist euler) so the next
  session shows the actual mismatch. Operator rule: at the click, hold the controllers like the robot holds its hands.
- Ending protocol: left-stick click (arms back to planner) → four-button hold or `O` (robot goes soft) → power off.
  Do NOT leave SONIC balancing unattended: it is a live policy holding the robot, ankle drivers heat up.

### Robot session 3 — 2026-09-04 18:01: mimicking the robot at the click makes the arms "more in shape"
Logged at the VR_3PT click (robot frame, euler xyz deg): robot L [63,66,20] R [-81,68,-33] vs operator
L [135,-10,63] R [-134,-11,-61] — mirror-symmetric, i.e. a clean constant per hand. Baked as FIXED controller→hand
constants (`~/patch_fixed_hand_offset.py`: C_L euler ≈ [2,-60,-74], C_R ≈ [-7,-53,76], wxyz in the file) so the
click no longer depends on how the operator holds the controllers — this is what the AGILE/IsaacTeleop retargeter
does (fixed anatomical constants, no mimicking). Position offsets are still calibrated at each click.
`SONIC_LEARN_HAND_OFFSET=1` re-learns them from a click. Torso now stays on the locked heading instead of turning
with the head (`_SYNTH_TORSO_FOLLOWS_HEAD=False`). Right ankle roll driver again 79 °C after ~7 min.
Decision (user, 2026-09-04 evening): keep behaviour vanilla — the torso follows the head as upstream does
(`_SYNTH_TORSO_FOLLOWS_HEAD = True`, reverted). Kept: locked root heading (a pelvis stand-in — upstream has a
tracked pelvis, which does not turn with the head) and the fixed controller→hand constants (no mimicking at the click).
