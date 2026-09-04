#!/bin/bash
# Gate C bring-up: deploy (zmq_manager, sim) -> MuJoCo sim on :99 (VirtualGL) -> Pico streamer (isaac-teleop / CloudXR in-process)
# Usage: ~/sonic_gateC.sh            (does NOT press ] or release the band; engage from the headset, then release with ~/sonic_drop.sh)
R=~/GR00T-WholeBodyControl
Y=$R/gear_sonic/utils/mujoco_sim/wbc_configs/g1_29dof_sonic_model12.yaml
cp $Y.orig $Y
export DISPLAY=:99 XAUTHORITY=$HOME/.Xauth-gdm
for s in sonic-deploy sonic-sim sonic-pico; do tmux kill-session -t $s 2>/dev/null; done; sleep 1
tmux new-session -d -s sonic-deploy -x 200 -y 50 "cd $R/gear_sonic_deploy && export PATH=/usr/local/cuda/bin:\$PATH CUDA_HOME=/usr/local/cuda && bash deploy.sh --input-type zmq_manager sim 2>&1 | tee ~/sonic_deploy_gateC.log; echo DEPLOY_EXIT; sleep 100000"
for i in $(seq 1 60); do sleep 2; tmux capture-pane -pt sonic-deploy | grep -q "Proceed with deployment" && break; done
tmux send-keys -t sonic-deploy Y Enter
for i in $(seq 1 60); do sleep 2; tmux capture-pane -pt sonic-deploy | grep -q "Init Done" && break; done; echo "deploy init: $(tmux capture-pane -pt sonic-deploy | grep -c "Init Done")"
tmux new-session -d -s sonic-sim -x 200 -y 50 "cd $R && source .venv_sim/bin/activate && export DISPLAY=:99 XAUTHORITY=$HOME/.Xauth-gdm && /opt/VirtualGL/bin/vglrun -d egl python gear_sonic/scripts/run_sim_loop.py 2>&1 | tee ~/sonic_sim_gateC.log; echo SIM_EXIT; sleep 100000"
for i in $(seq 1 20); do sleep 2; xwininfo -root -tree 2>/dev/null | grep -q MuJoCo && break; done; echo "sim window: $(xwininfo -root -tree 2>/dev/null | grep -c MuJoCo)"
tmux new-session -d -s sonic-pico -x 200 -y 50 "cd $R && source .venv_teleop/bin/activate && python gear_sonic/scripts/pico_manager_thread_server.py --manager --input-source isaac-teleop 2>&1 | tee ~/sonic_pico_gateC.log; echo PICO_EXIT; sleep 100000"
for i in $(seq 1 90); do sleep 2; grep -q "Isaac Teleop session initialized\|waiting for Isaac Teleop\|PICO_EXIT\|Error\|error" ~/sonic_pico_gateC.log 2>/dev/null && break; done
echo "== pico tail"; tail -15 ~/sonic_pico_gateC.log | cut -c1-200
echo "== 48322"; ss -ltn | grep 48322
tmux kill-session -t sonic-watch 2>/dev/null; : > ~/sonic_watchC.log; tmux new -d -s sonic-watch "~/sonic_watchC.sh"; echo "watcher restarted"
