#!/bin/bash
# (Re)start the headset sim panel on the CURRENT CloudXR runtime. Safe to run while a headset is connected.
tmux kill-session -t sonic-view 2>/dev/null
for p in $(pgrep -f "^python /home/physicalturing/sonic_sim_view.py"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill $p 2>/dev/null; done; sleep 1
: > ~/sonic_view.log
tmux new -d -s sonic-view "cd ~/GR00T-WholeBodyControl && source .venv_teleop/bin/activate && export DISPLAY=:99 XAUTHORITY=$HOME/.Xauth-gdm && python ~/sonic_sim_view.py 2>&1 | tee ~/sonic_view.log; echo VIEW_EXIT; sleep 100000"
for i in $(seq 1 30); do sleep 2; grep -q "running\|VIEW_EXIT\|Traceback" ~/sonic_view.log 2>/dev/null && break; done
sleep 5
L=~/.cloudxr/logs/$(ls -t ~/.cloudxr/logs | grep cxr_server | head -1)
echo "panel: $(grep -c 'sim_view\] running' ~/sonic_view.log)  xr clients: $(grep -c 'connected to pipe' $L) $(grep application_name $L | sed 's/.*: //' | tr '\n' ' ')  headset: $(ss -tn | grep 48322 | grep -c ESTAB)"
