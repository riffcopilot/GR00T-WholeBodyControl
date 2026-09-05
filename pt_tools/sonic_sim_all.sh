#!/bin/bash
# One-shot sim teleop bring-up: deploy + MuJoCo + Pico streamer (CloudXR) + spring watcher + headset sim panel.
# Then: headset -> client page -> Connect -> A+B+X+Y once -> A+B picks gait -> left stick walks -> left stick click = VR_3PT.
tmux kill-session -t sonic-view 2>/dev/null
~/sonic_gateC.sh 2>&1 | grep "sim window\|watcher\|Traceback"
: > ~/sonic_view.log
tmux new -d -s sonic-view "cd ~/GR00T-WholeBodyControl && source .venv_teleop/bin/activate && export DISPLAY=:99 XAUTHORITY=$HOME/.Xauth-gdm && python ~/sonic_sim_view.py 2>&1 | tee ~/sonic_view.log; echo VIEW_EXIT; sleep 100000"
for i in $(seq 1 30); do sleep 2; grep -q "running\|VIEW_EXIT\|Traceback" ~/sonic_view.log 2>/dev/null && break; done
grep "sim_view\] running\|RuntimeError" ~/sonic_view.log | tail -1
for i in $(seq 1 40); do sleep 3; tmux capture-pane -pt sonic-deploy | grep -q "Init Done" && break; done
echo "deploy Init Done: $(tmux capture-pane -pt sonic-deploy | grep -c "Init Done")   CloudXR ports: $(ss -ltn | grep -E "49100|48322" | wc -l)/3"
tmux kill-session -t sonic-cxrwd 2>/dev/null; tmux new -d -s sonic-cxrwd "~/sonic_cxr_watchdog.sh"; echo "cloudxr watchdog up"
