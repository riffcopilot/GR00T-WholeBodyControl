"""Derive per-episode wall-clock times + chirp anchors for a SONIC dataset and write them into
<dataset>/meta/episode_times.json (rsynced with the dataset; consumed by Seer's LeRobot ingest).

Sources: the stamped exporter log (~/sonic_export.log, lines "<unix> Started recording N" /
"Stopping recording, preparing to save" / "Discarded episode") and ~/sonic_say.log (one JSON line per
cue with play_sound's result — commanded_unix is the offload rig's audio anchor).

Usage: python3 sonic_episode_times.py <dataset_name_or_dir> [--export-log ~/sonic_export.log] [--say-log ~/sonic_say.log]
"""
import argparse, json, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument("dataset")
ap.add_argument("--export-log", default=os.path.expanduser("~/sonic_export.log"))
ap.add_argument("--say-log", default=os.path.expanduser("~/sonic_say.log"))
a = ap.parse_args()
D = a.dataset if os.path.isdir(a.dataset) else os.path.expanduser(f"~/sonic_datasets/{a.dataset}")
meta = os.path.join(D, "meta"); out_path = os.path.join(meta, "episode_times.json")
if not os.path.isdir(meta):
    print(f"no dataset at {D}", file=sys.stderr); sys.exit(1)
times = {}
if os.path.exists(out_path):
    try: times = json.load(open(out_path))
    except Exception: times = {}

# Only lines belonging to THIS dataset: the exporter log is truncated per exporter start, and the
# dataset name of the run is in ~/sonic_export.name — refuse to mix if it differs.
name_file = os.path.expanduser("~/sonic_export.name")
current = open(name_file).read().strip() if os.path.exists(name_file) else None
if current and current != os.path.basename(D.rstrip("/")):
    print(f"exporter log belongs to dataset {current!r}, not {os.path.basename(D)!r}; keeping existing times", file=sys.stderr)
    json.dump(times, open(out_path, "w"), indent=1); print(out_path); sys.exit(0)

cur = None
if os.path.exists(a.export_log):
    for raw in open(a.export_log, errors="replace"):
        m = re.match(r"^(\d+\.\d+) (.*)$", raw.rstrip("\n"))
        if not m: continue
        t, line = float(m.group(1)), m.group(2)
        ms = re.search(r"Started recording (\d+)", line)
        if ms:
            cur = int(ms.group(1)); times.setdefault(str(cur), {})["started_unix"] = t; continue
        if cur is None: continue
        if "Stopping recording" in line or "Discarded episode" in line:
            times.setdefault(str(cur), {})["ended_unix"] = t
            if "Discarded" in line: times[str(cur)]["discarded"] = True
            cur = None

# Chirp anchors: pair each say-log event with the nearest episode boundary (within 5 s).
cues = []
if os.path.exists(a.say_log):
    for raw in open(a.say_log, errors="replace"):
        try: cues.append(json.loads(raw))
        except Exception: pass
def nearest(key, t):
    best, bi = None, None
    for idx, ep in times.items():
        v = ep.get(key)
        if v is None: continue
        d = abs(v - t)
        if d < 5 and (best is None or d < best): best, bi = d, idx
    return bi
for c in cues:
    r = c.get("result"); ev = c.get("event", ""); t = float(c.get("t", 0))
    if not isinstance(r, dict) or not isinstance(r.get("commanded_unix"), (int, float)): continue
    if "Started recording" in ev:
        idx = nearest("started_unix", t)
        if idx: times[idx]["sound_start"] = r
    elif "Finished saving" in ev or "Saved episode" in ev:
        idx = nearest("ended_unix", t)
        if idx: times[idx]["sound_stop"] = r
json.dump(times, open(out_path, "w"), indent=1)
print(out_path)
