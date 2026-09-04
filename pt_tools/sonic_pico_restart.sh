#!/bin/bash
# Restart only the Pico streamer (deploy + sim untouched)
R=~/GR00T-WholeBodyControl
tmux kill-session -t sonic-pico 2>/dev/null; sleep 3
for p in $(pgrep -f "^python gear_sonic/scripts/pico_manager_thread_server|bin/python -c import sys, os"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill $p 2>/dev/null; done; sleep 2
ss -ltn | grep -q 48322 && echo "48322 still bound"
tmux new-session -d -s sonic-pico -x 200 -y 50 "cd $R && source .venv_teleop/bin/activate && python gear_sonic/scripts/pico_manager_thread_server.py --manager --input-source isaac-teleop ${PICO_EXTRA} 2>&1 | tee ${PICO_LOG:-$HOME/sonic_pico_gateC.log}; echo PICO_EXIT; sleep 100000"
for i in $(seq 1 60); do sleep 2; grep -q "waiting for Isaac Teleop body data\|PICO_EXIT\|Traceback" ${PICO_LOG:-$HOME/sonic_pico_gateC.log} 2>/dev/null && break; done
grep -v "XR_ERROR_FEATURE_UNSUPPORTED\|ipc_client_system_devices\|^serial:\|^name:" ${PICO_LOG:-$HOME/sonic_pico_gateC.log} | grep -i "initialized\|Traceback\|Error\|waiting\|synthetic" | tail -6 | cut -c1-200
echo "== wss"; tail -3 ~/.cloudxr/logs/$(ls -t ~/.cloudxr/logs | grep wss | head -1) | cut -c1-160
ss -ltn | grep 48322 | head -1
# The headset sim panel is a separate OpenXR app on the runtime — restart it whenever the runtime is.
if pgrep -f "^python /home/physicalturing/sonic_sim_view.py" >/dev/null || tmux has-session -t sonic-view 2>/dev/null; then ~/sonic_view_start.sh; fi
