#!/bin/bash
# Start NVIDIA's SONIC data exporter (LeRobot/GR00T dataset writer) — tmux sonic-export → ~/sonic_export.log.
#   sonic_exporter_start.sh "<task prompt>" [dataset_name]
# Dataset lands in ~/sonic_datasets/<dataset_name>/ (parquet + mp4 + meta/info.json + meta/modality.json).
# Sources: g1_debug (deploy, ZMQ 5557), pose/planner/manager_state (streamer, ZMQ 5556), camera server (5555).
# The deploy re-publishes robot_config every ~2 s and g1_debug only while the policy runs (CONTROL), so the
# exporter can start any time; it idles until Engage + the headset combo. A running exporter beside the deploy is harmless. Keys come from ~/sonic_record.sh via the relay on :5580.
TASK=${1:-demo}
NAME=${2:-$(date +%Y-%m-%d-%H-%M-%S)}
[ -x ~/GR00T-WholeBodyControl/.venv_data_collection/bin/python ] || { echo "no .venv_data_collection — run install_scripts/install_data_collection.sh"; exit 1; }
ss -ltn | grep -q ":5555 " || echo "warning: camera server not up on :5555 (sonic_camera_start.sh) — the exporter will wait for frames"
tmux kill-session -t sonic-export 2>/dev/null
for p in $(pgrep -f "gear_sonic/scripts/run_data_exporte[r]"); do [ "$p" != "$$" ] && [ "$p" != "$PPID" ] && kill $p 2>/dev/null; done; sleep 1
mkdir -p ~/sonic_datasets
printf '%s' "$TASK" > ~/sonic_export.task
printf '%s' "$NAME" > ~/sonic_export.name
: > ~/sonic_export.log
tmux new -d -s sonic-export "cd ~/GR00T-WholeBodyControl && source .venv_data_collection/bin/activate && export SONIC_SAY_CMD=$HOME/sonic_say.sh && python -u gear_sonic/scripts/run_data_exporter.py --task-prompt \"\$(cat $HOME/sonic_export.task)\" --dataset-name \"\$(cat $HOME/sonic_export.name)\" --root-output-dir $HOME/sonic_datasets --camera-host localhost --camera-port 5555 2>&1 | python3 -u $HOME/sonic_ts.py | tee ~/sonic_export.log; echo EXPORT_EXIT; sleep 100000"
# lerobot + the robot model take ~30 s to import before the first line appears
for i in $(seq 1 90); do sleep 1; grep -aq "robot_config\|Waiting for message\|ZMQKeyboardSubscriber\|EXPORT_EXIT\|Traceback" ~/sonic_export.log 2>/dev/null && break; done
if grep -aq "EXPORT_EXIT\|Traceback" ~/sonic_export.log; then echo "exporter FAILED:"; grep -av "^\s*$" ~/sonic_export.log | tail -5 | cut -c1-140; exit 1; fi
~/sonic_record.sh >/dev/null 2>&1; tmux has-session -t sonic-keys 2>/dev/null || { : > ~/sonic_keys.log; tmux new -d -s sonic-keys "cd ~/GR00T-WholeBodyControl && .venv_teleop/bin/python $HOME/sonic_keys_relay.py 2>&1 | tee ~/sonic_keys.log"; }
echo "exporter up: task='$TASK' dataset=~/sonic_datasets/$NAME (idle until the policy runs — it records only while the deploy publishes state)"
