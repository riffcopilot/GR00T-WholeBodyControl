#!/bin/bash
R=~/GR00T-WholeBodyControl
Y=$R/gear_sonic/utils/mujoco_sim/wbc_configs/g1_29dof_sonic_model12.yaml
cp $Y.orig $Y
B=$R/gear_sonic/utils/mujoco_sim/unitree_sdk2py_bridge.py
grep -q "ElasticBand enable (viewer)" $B || $R/.venv_sim/bin/python - "$B" <<"PY"
import sys,re
p=sys.argv[1]; s=open(p).read()
old="        if key == glfw.KEY_9:\n            self.enable = not self.enable\n"
new=old+"            print(f\"ElasticBand enable (viewer): {self.enable}\", flush=True)\n"
assert old in s; open(p,"w").write(s.replace(old,new,1)); print("patched")
PY
tmux kill-session -t sonic-deploy 2>/dev/null; tmux kill-session -t sonic-sim 2>/dev/null; sleep 1
tmux new-session -d -s sonic-deploy -x 200 -y 50 "cd $R/gear_sonic_deploy && export PATH=/usr/local/cuda/bin:\$PATH CUDA_HOME=/usr/local/cuda && bash deploy.sh --input-type keyboard sim 2>&1 | tee ~/sonic_deploy_run2.log; echo DEPLOY_EXIT; sleep 100000"
for i in $(seq 1 60); do sleep 2; tmux capture-pane -pt sonic-deploy | grep -q "Proceed with deployment" && break; done
tmux send-keys -t sonic-deploy Y Enter
for i in $(seq 1 60); do sleep 2; tmux capture-pane -pt sonic-deploy | grep -q "Init Done" && break; done; echo "deploy init: $(tmux capture-pane -pt sonic-deploy | grep -c "Init Done")"
tmux new-session -d -s sonic-sim -x 200 -y 50 "cd $R && source .venv_sim/bin/activate && export DISPLAY=${SIMDISP:-:99} XAUTHORITY=$HOME/.Xauth-gdm && ${SIMVGL:+/opt/VirtualGL/bin/vglrun -d egl} python gear_sonic/scripts/run_sim_loop.py 2>&1 | tee ~/sonic_sim_run3.log; echo SIM_EXIT; sleep 100000"
for i in $(seq 1 20); do sleep 2; DISPLAY=${SIMDISP:-:99} XAUTHORITY=$HOME/.Xauth-gdm xwininfo -root -tree 2>/dev/null | grep -q MuJoCo && break; done; sleep 3
tmux send-keys -t sonic-deploy "]"; sleep 4
export DISPLAY=${SIMDISP:-:99} XAUTHORITY=$HOME/.Xauth-gdm; W=$(xdotool search --name "MuJoCo" | head -1); xdotool windowfocus --sync $W; xdotool key 9; sleep 1
tmux capture-pane -pt sonic-sim | grep "ElasticBand" | tail -2
sleep 30
import -window root ~/sonic_shots/05_gateA_30s.png
cd $R && .venv_sim/bin/python ~/sonic_stand.py
echo "== deploy tail"; tmux capture-pane -pt sonic-deploy | grep -v "^\s*$" | tail -2 | cut -c1-140
