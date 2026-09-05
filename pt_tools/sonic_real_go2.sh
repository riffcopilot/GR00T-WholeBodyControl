#!/bin/bash
# Answer the deploy prompt (MOTORS ENGAGE: 3 s ramp to the default stand, then rigid hold), then guard the hold phase:
# wait up to $1 s (default 90) for the headset's A+B+X+Y (deploy logs "transitioning to CONTROL state");
# if any motor/driver temperature reaches 90 C first, press O (damping) and abort.
WAIT=${1:-90}
tmux capture-pane -pt sonic-deploy | grep -q "Proceed with deployment" || { echo "deploy is not at the Proceed prompt"; exit 1; }
L=~/sonic_deploy_real.log; N0=$(grep -ac "transitioning to CONTROL state" $L)
tmux send-keys -t sonic-deploy Y Enter
for i in $(seq 1 60); do sleep 1; tmux capture-pane -pt sonic-deploy | grep -q "Init Done\|DEPLOY_EXIT\|Safety check\|Failed" && break; done
echo "$(date +%T) $(tmux capture-pane -pt sonic-deploy | grep -a "Init Done\|DEPLOY_EXIT\|Safety\|Failed" | tail -1)"
echo "$(date +%T) holding default stand — waiting up to ${WAIT}s for the headset combo (temp guard 90C)"
for i in $(seq 1 $WAIT); do
  sleep 1
  if [ "$(grep -ac "transitioning to CONTROL state" $L)" -gt "$N0" ]; then echo "$(date +%T) POLICY ACTIVE (CONTROL state)"; tail -1 ~/sonic_temps.log; exit 0; fi
  if tail -1 ~/sonic_temps.log | grep -q ">=90"; then echo "$(date +%T) TEMP >= 90C during hold — pressing O"; tail -1 ~/sonic_temps.log; tmux send-keys -t sonic-deploy O; exit 2; fi
  if tmux capture-pane -pt sonic-deploy | grep -q "DEPLOY_EXIT"; then echo "$(date +%T) deploy exited"; exit 3; fi
  [ $((i % 15)) = 0 ] && echo "$(date +%T) still holding: $(tail -1 ~/sonic_temps.log | cut -c9-70)"
done
echo "$(date +%T) no combo within ${WAIT}s — pressing O to end the rigid hold"; tmux send-keys -t sonic-deploy O; exit 4
