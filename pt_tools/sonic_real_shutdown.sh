#!/bin/bash
# Orderly end of a real-robot session: wrist snapshot -> O (damping) -> streamer/guard/watchers down.
cd ~/GR00T-WholeBodyControl
echo "== wrist/forearm motors before stop"
timeout 15 .venv_sim/bin/python - <<'PY' 2>&1 | tail -3
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
ChannelFactoryInitialize(0, "enP2p1s0"); st={}
s=ChannelSubscriber("rt/lowstate", LowState_); s.Init(lambda m: st.__setitem__("m",m),10)
t0=time.time()
while "m" not in st and time.time()-t0<5: time.sleep(0.05)
m=st["m"]
names={18:"L_elbow",19:"L_wr_roll",20:"L_wr_pitch",21:"L_wr_yaw",25:"R_elbow",26:"R_wr_roll",27:"R_wr_pitch",28:"R_wr_yaw"}
print([(n, "q=%.2f"%m.motor_state[i].q, "tau=%.1f"%m.motor_state[i].tau_est, "T=%d/%d"%(m.motor_state[i].temperature[0],m.motor_state[i].temperature[1]), "st=%d"%m.motor_state[i].motorstate) for i,n in names.items()])
PY
echo "== stop deploy (O -> damping)"
tmux send-keys -t sonic-deploy O; for i in $(seq 1 20); do sleep 1; tmux capture-pane -pt sonic-deploy | grep -q "DEPLOY_EXIT" && break; done
tmux capture-pane -pt sonic-deploy | grep -a "Stop\|DEPLOY_EXIT" | tail -2
for s in sonic-guard sonic-go sonic-pico sonic-temps sonic-deploy; do tmux kill-session -t $s 2>/dev/null; done; sleep 3
echo "== leftovers"; ps -eo pid,args | grep "[g]1_deploy_onnx_ref\|[p]ico_manager_thread\|[_]RUNTIME_WORKER\|[s]onic_temp_watch" | cut -c1-80
echo "== bus after"; timeout 20 .venv_sim/bin/python ~/sonic_bus_check.py 2 2>&1 | grep "rt/lowcmd\|ROBOT\|BUS"
