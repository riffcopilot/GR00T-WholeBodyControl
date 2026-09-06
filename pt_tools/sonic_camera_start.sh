#!/bin/bash
# (Re)start NVIDIA's composed camera server on the G1 head camera (RealSense D435i RGB, UVC index 4) —
# tmux sonic-cam → ~/sonic_cam.log, ZMQ PUB on tcp://*:5555 (base64 JPEG frames, ~30 fps, 640×480).
# This is THE single owner of /dev/video4 in the SONIC world: the data exporter and the headset ego-view
# panel both subscribe to it (one claimant, two consumers). Runs in .venv_teleop (gear_sonic + cv2 + zmq).
PORT=${SONIC_CAM_PORT:-5555}
tmux kill-session -t sonic-cam 2>/dev/null
for p in $(pgrep -f "gear_sonic.camera.composed_camer[a]"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill $p 2>/dev/null; done; sleep 1
: > ~/sonic_cam.log
tmux new -d -s sonic-cam "cd ~/GR00T-WholeBodyControl && source .venv_teleop/bin/activate && python -u -m gear_sonic.camera.composed_camera --ego-view-camera usb --ego-view-device-id ${SONIC_CAM_DEVICE:-4} --port $PORT --fps 30 2>&1 | tee ~/sonic_cam.log; echo CAM_EXIT; sleep 100000"
for i in $(seq 1 40); do sleep 1; grep -q "Sensor server running\|CAM_EXIT\|Traceback" ~/sonic_cam.log 2>/dev/null && break; done
if grep -q "Sensor server running" ~/sonic_cam.log && ss -ltn | grep -q ":$PORT "; then echo "camera server up on :$PORT (/dev/video${SONIC_CAM_DEVICE:-4})"; exit 0; fi
echo "camera server FAILED:"; grep -v "^\s*$" ~/sonic_cam.log | tail -4; exit 1
