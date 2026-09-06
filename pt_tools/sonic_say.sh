#!/bin/bash
# Audio cue for the SONIC data exporter, through the G1's own head speaker (audible under the headset).
# Called by the exporter's TextToSpeech fallback (SONIC_SAY_CMD) with the message as $1; only the
# recording events make a sound, and each event has its own waveform (g1-capture thor/play_sound.py,
# the offload rig's anchor player — DDS + PCM, needs the robot on; silent failure otherwise):
#   "Started recording"  -> notes       (ascending run)
#   "Finished saving"    -> notes_desc  (descending run)
#   "Discarded episode"  -> birdy
case "$1" in
  *"Started recording"*) WAVE=notes ;;
  *"Finished saving"*|*"Saved episode"*) WAVE=notes_desc ;;
  *"Discarded episode"*) WAVE=birdy ;;
  *) exit 0 ;;
esac
PY=$HOME/miniforge3/envs/tv/bin/python
[ -x "$PY" ] || PY=$HOME/GR00T-WholeBodyControl/.venv_sim/bin/python
timeout 6 "$PY" "$HOME/g1-capture/thor/play_sound.py" --wave "$WAVE" --dur 0.6 --json >> "$HOME/sonic_say.log" 2>&1 || echo "$(date +%T) say '$WAVE' failed (robot off?)" >> "$HOME/sonic_say.log"
exit 0
