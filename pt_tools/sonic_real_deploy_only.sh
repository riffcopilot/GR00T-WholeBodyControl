#!/bin/bash
# Restart just the real-robot deploy to its Proceed prompt (streamer/CloudXR left running). Bus check first.
R=~/GR00T-WholeBodyControl
[ "$(cat /sys/class/net/enP2p1s0/carrier 2>/dev/null)" = "1" ] || { echo "ABORT: robot link down"; exit 1; }
pgrep -f target/release/g1_deploy_onnx_ref >/dev/null && { echo "ABORT: a deploy is already running"; exit 1; }
cd $R && timeout 20 .venv_sim/bin/python ~/sonic_bus_check.py 3 | grep "BUS\|ROBOT"; [ "${PIPESTATUS[0]}" = "0" ] || { echo "ABORT: bus check failed"; exit 1; }
tmux kill-session -t sonic-deploy 2>/dev/null; sleep 1
tmux new-session -d -s sonic-deploy -x 200 -y 50 "cd $R/gear_sonic_deploy && export PATH=/usr/local/cuda/bin:\$PATH CUDA_HOME=/usr/local/cuda && bash deploy.sh --input-type zmq_manager real 2>&1 | tee -a ~/sonic_deploy_real.log; echo DEPLOY_EXIT; sleep 100000"
for i in $(seq 1 60); do sleep 2; tmux capture-pane -pt sonic-deploy | grep -q "Proceed with deployment\|DEPLOY_EXIT\|rror" && break; done
tmux capture-pane -pt sonic-deploy | grep -a "Proceed\|enP2p1s0\|rror" | tail -3 | cut -c1-120
