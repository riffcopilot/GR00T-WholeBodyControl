#!/bin/bash
# Audio cue for the SONIC data exporter, through the G1's own head speaker (audible under the headset).
# Called by the exporter's TextToSpeech fallback (SONIC_SAY_CMD) with the message as $1; only the
# recording events make a sound, and each event has its own waveform (g1-capture thor/play_sound.py,
# the offload rig's anchor player — DDS + PCM, needs the robot on; silent failure otherwise):
#   "Started recording"  -> notes       (ascending run  = the rig's START anchor template)
#   "Finished saving"    -> notes_desc  (descending run = the rig's STOP anchor template)
#   "Discarded episode"  -> birdy
# Every call appends one JSON line to ~/sonic_say.log: {"t": unix, "event": "...", "wave": "...", "result": <play_sound --json or null>}
# — sonic_episode_times.py turns those into per-episode wall times + chirp anchors for the Seer ingest.
MSG=$1
case "$MSG" in
  *"Started recording"*) WAVE=notes ;;
  *"Finished saving"*|*"Saved episode"*) WAVE=notes_desc ;;
  *"Discarded episode"*) WAVE=birdy ;;
  *) exit 0 ;;
esac
PY=$HOME/miniforge3/envs/tv/bin/python
[ -x "$PY" ] || PY=$HOME/GR00T-WholeBodyControl/.venv_sim/bin/python
T=$(date +%s.%N | cut -c1-14)
RES=$(timeout 6 "$PY" "$HOME/g1-capture/thor/play_sound.py" --wave "$WAVE" --dur 1.0 --json 2>/dev/null | grep -a "^{" | tail -1)
[ -n "$RES" ] || RES=null
printf '{"t": %s, "event": %s, "wave": "%s", "result": %s}\n' "$T" "$(printf '%s' "$MSG" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" "$WAVE" "$RES" >> "$HOME/sonic_say.log"
exit 0
