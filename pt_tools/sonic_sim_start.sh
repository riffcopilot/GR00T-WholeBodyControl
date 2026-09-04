#!/bin/bash
pkill -x Xvfb 2>/dev/null; pkill -x x11vnc 2>/dev/null; tmux kill-session -t sonic-sim 2>/dev/null; sleep 1
nohup Xvfb :99 -screen 0 1600x1000x24 +extension GLX +render -noreset > ~/xvfb.log 2>&1 < /dev/null &
sleep 2
nohup x11vnc -display :99 -localhost -forever -shared -nopw -quiet -rfbport 5999 > ~/x11vnc.log 2>&1 < /dev/null &
sleep 1
tmux new-session -d -s sonic-sim -x 200 -y 50 "cd ~/GR00T-WholeBodyControl && source .venv_sim/bin/activate && export DISPLAY=:99 && python gear_sonic/scripts/run_sim_loop.py 2>&1 | tee ~/sonic_sim_run1.log; echo SIM_EXIT; sleep 100000"
for i in $(seq 1 30); do sleep 3; tmux capture-pane -pt sonic-sim | grep -qi "error\|Traceback\|SIM_EXIT\|simulat\|running\|ready\|viewer" && break; done
echo "== sim pane"; tmux capture-pane -pt sonic-sim | grep -v "^\s*$" | tail -25 | cut -c1-200
echo "== windows on :99"; DISPLAY=:99 xwininfo -root -tree 2>/dev/null | grep -i "mujoco\|children" | head -3
echo "== tools"; command -v ffmpeg xwd glxinfo
echo "== deploy pane"; tmux capture-pane -pt sonic-deploy | grep -v "^\s*$" | tail -6 | cut -c1-200
ls ~/GR00T-WholeBodyControl/gear_sonic_deploy/planner/target_vel/V2/
