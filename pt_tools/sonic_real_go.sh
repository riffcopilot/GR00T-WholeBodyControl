#!/bin/bash
# Answer Y to the real-robot deploy prompt. THIS ENGAGES THE MOTORS: the deploy ramps every joint to the default standing pose over 3 s (INIT) and holds it (WAIT_FOR_CONTROL) until the headset A+B+X+Y starts the policy. Robot must be on the gantry, slack, feet near the floor.
tmux capture-pane -pt sonic-deploy | grep -q "Proceed with deployment" || { echo "deploy is not at the Proceed prompt"; exit 1; }
tmux send-keys -t sonic-deploy Y Enter
for i in $(seq 1 90); do sleep 2; tmux capture-pane -pt sonic-deploy | grep -q "Init Done\|DEPLOY_EXIT\|Safety check\|Failed" && break; done
tmux capture-pane -pt sonic-deploy | grep -v "^\s*$\|LowState is not" | tail -10 | cut -c1-160
echo "Init Done: $(tmux capture-pane -pt sonic-deploy | grep -c "Init Done")"
