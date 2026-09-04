#!/bin/bash
# CloudXR signaling watchdog: if the runtime logs "Endpoint unresponsive" after its last "Signaling server started"
# while NO headset is connected, restart the streamer (runtime comes with it). Never touches a live session.
LOG=${PICO_LOG:-$HOME/sonic_pico_gateC.log}
while true; do
  sleep 10
  N=$(ls -t ~/.cloudxr/logs/cxr_streamsdk* 2>/dev/null | head -1); [ -z "$N" ] && continue
  pgrep -f "pico_manager_thread_serve" >/dev/null || continue
  started=$(grep -n "Signaling server started" "$N" | tail -1 | cut -d: -f1)
  dead=$(grep -n "Endpoint unresponsive" "$N" | tail -1 | cut -d: -f1)
  [ -n "$dead" ] && [ "${dead:-0}" -gt "${started:-0}" ] || continue
  if [ "$(ss -tn | grep 48322 | grep -c ESTAB)" = "0" ]; then
    echo "$(date +%T) signaling dead (line $dead > $started), no headset connected -> restarting streamer" >> ~/sonic_cxr_watchdog.log
    PICO_LOG=$LOG ~/sonic_pico_restart.sh >> ~/sonic_cxr_watchdog.log 2>&1
    sleep 30
  fi
done
