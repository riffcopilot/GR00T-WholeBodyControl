#!/bin/bash
# Gate C watcher: releases the MuJoCo elastic band 3 s after the deploy enters CONTROL (the headset's A+B+X+Y), once.
L=~/sonic_deploy_gateC.log; P=~/sonic_pico_gateC.log; O=~/sonic_watchC.log
dropped=0; conn=0
while true; do
  if [ $conn = 0 ] && grep -q "Fresh data received\|DeviceIO data\|connection restored\|client connected" $P 2>/dev/null; then conn=1; echo "$(date +%T) headset data seen" >> $O; fi
  if [ $dropped = 0 ] && grep -q "transitioning to CONTROL state" $L 2>/dev/null; then
    echo "$(date +%T) CONTROL state -> releasing band in 3 s" >> $O; sleep 3; ~/sonic_drop.sh >> $O 2>&1; dropped=1
  fi
  sleep 1
done
