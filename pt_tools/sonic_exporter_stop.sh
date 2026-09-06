#!/bin/bash
# Stop the SONIC data exporter (and the key relay). An episode still RECORDING is discarded by the exporter's
# own shutdown handling — press Save (c) first if you want it kept.
for s in sonic-export sonic-keys; do tmux kill-session -t $s 2>/dev/null; done
for p in $(pgrep -f "gear_sonic/scripts/run_data_exporte[r]|sonic_keys_rela[y]"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill $p 2>/dev/null; done; sleep 1
N=$(cat ~/sonic_export.name 2>/dev/null)
[ -n "$N" ] && [ -d ~/sonic_datasets/$N ] && echo "dataset: ~/sonic_datasets/$N ($(ls ~/sonic_datasets/$N/data/chunk-* 2>/dev/null | grep -c parquet) episode parquet files)" || echo "no dataset written"
