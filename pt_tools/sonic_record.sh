#!/bin/bash
# Send a recording key to NVIDIA's SONIC data exporter through the key relay (tmux sonic-keys):
#   sonic_record.sh c   → exporter toggles: idle → RECORDING → stop+save → idle (one key each)
#   sonic_record.sh x   → discard the episode being recorded
# Starts the relay if it is not running. The exporter (tmux sonic-export) must be up to hear it.
KEY=$1
case "$KEY" in c|x) ;; *) echo "usage: $0 c|x"; exit 2;; esac
if ! tmux has-session -t sonic-keys 2>/dev/null; then
  : > ~/sonic_keys.log
  tmux new -d -s sonic-keys "cd ~/GR00T-WholeBodyControl && .venv_teleop/bin/python $HOME/sonic_keys_relay.py 2>&1 | tee ~/sonic_keys.log"
  for i in $(seq 1 20); do sleep 0.5; grep -q "relay up" ~/sonic_keys.log 2>/dev/null && break; done
  sleep 1  # let the exporter's SUB (re)connect before the first key
fi
tmux has-session -t sonic-export 2>/dev/null || echo "warning: no exporter running (tmux sonic-export) — key will go nowhere"
timeout 3 bash -c "echo $KEY > $HOME/sonic_keys.fifo" || { echo "relay did not accept the key (fifo blocked)"; exit 1; }
sleep 1.2
echo "sent '$KEY' — exporter: $(grep -a 'Started recording\|Stopping recording\|Saved episode\|Discarded episode' ~/sonic_export.log 2>/dev/null | tail -1 | cut -c1-100)"
