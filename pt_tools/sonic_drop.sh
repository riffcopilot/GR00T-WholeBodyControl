#!/bin/bash
# Release the MuJoCo elastic band (press 9 in the sim window on :99)
export DISPLAY=:99 XAUTHORITY=$HOME/.Xauth-gdm
W=$(xdotool search --name "MuJoCo" | head -1); xdotool windowactivate --sync $W 2>/dev/null; xdotool windowfocus --sync $W 2>/dev/null; sleep 0.3; xdotool key 9; sleep 1
tmux capture-pane -pt sonic-sim | grep "ElasticBand" | tail -1
