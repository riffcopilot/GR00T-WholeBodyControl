"""SIM-ONLY stand-in for the Pico streamer's manager: binds the manager PUB (:5556), sends the deploy the
`command` start the headset combo sends, then streams pose/planner/manager_state at --hz like the real
streamer (load realism for the exporter's queue) and fires the grip-combo recording toggles
(manager_state toggle_data_collection / toggle_data_abort, one-tick pulses) on a schedule:
  --toggles "c:5,c:35,c:40,x:45,c:50,c:80"   key:seconds-after-start (c = toggle, x = discard)
Toggle wall-clock times go to ~/sonic_fakemgr_toggles.log for rate measurement. Never run against the real robot."""
import argparse, importlib.util, sys, time, zmq, numpy as np
ap = argparse.ArgumentParser(); ap.add_argument("--hz", type=float, default=100); ap.add_argument("--toggles", default=""); ap.add_argument("--vr3pt", action="store_true")
a = ap.parse_args(); sys.argv = ["x"]
spec = importlib.util.spec_from_file_location("pm", "gear_sonic/scripts/pico_manager_thread_server.py")
pm = importlib.util.module_from_spec(spec); spec.loader.exec_module(pm)
ctx = zmq.Context(); s = ctx.socket(zmq.PUB); s.bind("tcp://*:5556"); time.sleep(1.0)
for i in range(5):
    s.send(pm.build_command_message(start=True, stop=False, planner=True)); print("[fake manager] sent start", i, flush=True); time.sleep(1.0)
sched = []
for tok in filter(None, a.toggles.split(",")):
    k, t = tok.split(":"); sched.append((float(t), k))
sched.sort(); t0 = time.monotonic(); log = open(__import__("os").path.expanduser("~/sonic_fakemgr_toggles.log"), "a")
period = 1.0 / a.hz; nxt = time.monotonic(); n = 0
print(f"[fake manager] streaming manager_state/planner at {a.hz} Hz; toggles {sched}", flush=True)
while True:
    now = time.monotonic(); el = now - t0
    dc = da = False
    while sched and el >= sched[0][0]:
        t, k = sched.pop(0); dc = dc or k == "c"; da = da or k == "x"
        log.write(f"{time.time():.3f} {k}\n"); log.flush(); print(f"[fake manager] toggle {k} at +{el:.1f}s", flush=True)
    s.send(pm.pack_pose_message({"stream_mode": np.array([5 if a.vr3pt else 1], dtype=np.int32), "toggle_data_collection": np.array([dc], dtype=bool), "toggle_data_abort": np.array([da], dtype=bool)}, topic="manager_state"))
    s.send(pm.pack_pose_message({"mode": np.array([0], dtype=np.int32), "movement": np.zeros(3, dtype=np.float32), "facing": np.zeros(3, dtype=np.float32), "speed": np.zeros(1, dtype=np.float32), "height": np.zeros(1, dtype=np.float32)}, topic="planner"))
    n += 1; nxt += period; d = nxt - time.monotonic()
    if d > 0: time.sleep(d)
