#!/bin/bash
# Thermal guard: press O in the deploy pane when the temp watcher reports any motor/driver >= 90 C.
while sleep 1; do
  if tail -1 ~/sonic_temps.log 2>/dev/null | grep -q ">=90"; then
    echo "$(date +%T) TEMP >= 90C — pressing O: $(tail -1 ~/sonic_temps.log)" | tee -a ~/sonic_guard.log
    tmux send-keys -t sonic-deploy O; sleep 30
  fi
done
