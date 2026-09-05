#!/bin/bash
# Real-robot SONIC bring-up. Deliberately TWO steps:
#   ~/sonic_real.sh        : preflight (bus quiet, no other stack, link up) -> start deploy `real` and STOP at its "Proceed" prompt; start the Pico streamer
#   ~/sonic_real_go.sh     : answer Y to the deploy prompt (motors stay untouched until the headset's A+B+X+Y; INIT then ramps to the default stand over 3 s)
R=~/GR00T-WholeBodyControl
echo "== preflight"
[ "$(cat /sys/class/net/enP2p1s0/carrier 2>/dev/null)" = "1" ] || { echo "ABORT: robot link enP2p1s0 has no carrier (robot off / cable)"; exit 1; }
if ps -eo args | grep -q "[t]eleop_node\|[r]os2_control_node\|[x]r_teleoperate\|[t]eleop_ros2_node"; then echo "ABORT: another control stack is running:"; ps -eo pid,args | grep "[t]eleop_node\|[r]os2_control_node\|[x]r_teleoperate\|[t]eleop_ros2_node" | cut -c1-120; exit 1; fi
docker ps --format '{{.Names}}' | grep -q isaac_ros_dev_container && { echo "ABORT: isaac_ros_dev_container is up (AGILE/GR00T world)"; exit 1; }
pgrep -f run_sim_loop.py >/dev/null && { echo "ABORT: MuJoCo sim is still running (tmux sonic-sim) — kill it first"; exit 1; }
cd $R && timeout 20 .venv_sim/bin/python ~/sonic_bus_check.py 3 || { echo "ABORT: bus not quiet"; exit 1; }
echo "== deploy (real) — will wait at the Proceed prompt"
for s in sonic-deploy sonic-pico sonic-watch sonic-view; do tmux kill-session -t $s 2>/dev/null; done; sleep 1
tmux new-session -d -s sonic-deploy -x 200 -y 50 "cd $R/gear_sonic_deploy && export PATH=/usr/local/cuda/bin:\$PATH CUDA_HOME=/usr/local/cuda && bash deploy.sh --input-type zmq_manager real 2>&1 | tee ~/sonic_deploy_real.log; echo DEPLOY_EXIT; sleep 100000"
for i in $(seq 1 60); do sleep 2; tmux capture-pane -pt sonic-deploy | grep -q "Proceed with deployment\|DEPLOY_EXIT\|rror" && break; done
tmux capture-pane -pt sonic-deploy | grep -v "^\s*$" | tail -12 | cut -c1-160
echo "== streamer"
: > ~/sonic_pico_real.log
tmux new-session -d -s sonic-pico -x 200 -y 50 "cd $R && source .venv_teleop/bin/activate && python gear_sonic/scripts/pico_manager_thread_server.py --manager --input-source isaac-teleop 2>&1 | tee ~/sonic_pico_real.log; echo PICO_EXIT; sleep 100000"
for i in $(seq 1 90); do sleep 2; grep -q "waiting for Isaac Teleop body data\|PICO_EXIT\|Traceback" ~/sonic_pico_real.log 2>/dev/null && break; done
grep -v "XR_ERROR_FEATURE_UNSUPPORTED\|ipc_client" ~/sonic_pico_real.log | grep -i "initialized\.\|waiting for Isaac\|Traceback" | tail -2
echo "CloudXR ports: $(ss -ltn | grep -E "49100|48322" | wc -l)/3"
echo "NEXT: review the deploy pane (interface, mode release), then ~/sonic_real_go.sh"
tmux kill-session -t sonic-cxrwd 2>/dev/null; tmux new -d -s sonic-cxrwd "PICO_LOG=$HOME/sonic_pico_real.log ~/sonic_cxr_watchdog.sh"; echo "cloudxr watchdog up"
