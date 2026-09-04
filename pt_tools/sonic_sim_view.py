"""Show the MuJoCo sim window (Xvfb :99) as a Televiz panel inside the headset.

Second OpenXR app on the running CloudXR runtime (same trick as the AGILE kit's
Televiz camera panel). Grabs the X window region with mss, uploads to a CUDA torch tensor, and
submits it to a lazy-locked quad layer via camera_viz's pipeline/placements.

Usage (in .venv_teleop, DISPLAY=:99):
  python ~/sonic_sim_view.py [--region X,Y,W,H] [--fps 30] [--width-m 1.4] [--distance 1.6] [--lock lazy|head|world]
"""
import argparse, os, subprocess, sys, threading, time
from pathlib import Path

for line in open(os.path.expanduser("~/.cloudxr/run/cloudxr.env")):
    line = line.strip()
    if line.startswith("export "):
        k, v = line[7:].split("=", 1); os.environ.setdefault(k, v)

CV = Path.home() / "workspaces/isaac_ros-dev/IsaacTeleop/examples/camera_viz"
sys.path.insert(0, str(CV))
import numpy as np
import torch
import mss
import isaacteleop.viz as viz
from pipeline import Frame, FrameSource, SourceSpec, VizRunner
from placements import PlacementConfig, build as build_placement


def mujoco_region():
    try:
        wid = subprocess.check_output(["xdotool", "search", "--name", "MuJoCo"], text=True).split()[0]
        geo = subprocess.check_output(["xdotool", "getwindowgeometry", "--shell", wid], text=True)
        d = dict(l.split("=") for l in geo.split())
        return int(d["X"]), int(d["Y"]), int(d["WIDTH"]), int(d["HEIGHT"])
    except Exception as e:
        print(f"[sim_view] xdotool lookup failed ({e}); using 0,0,1066,666", flush=True)
        return 0, 0, 1066, 666


class ScreenSource(FrameSource):
    def __init__(self, name, region, fps):
        x, y, w, h = region
        w -= w % 2; h -= h % 2
        self._mon = {"left": x, "top": y, "width": w, "height": h}
        self._spec = SourceSpec(name=name, width=w, height=h, pixel_format="rgba8")
        self._interval = 1.0 / fps
        self._bufs = [torch.zeros((h, w, 4), dtype=torch.uint8, device="cuda") for _ in range(3)]
        self._write = 0; self._pub = -1; self._consumed = -2
        self._lock = threading.Lock(); self._stop = threading.Event(); self._thread = None
        self._n = 0

    @property
    def spec(self): return self._spec
    def start(self):
        self._stop.clear(); self._thread = threading.Thread(target=self._loop, daemon=False); self._thread.start()
    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(); self._thread = None
    def latest(self):
        with self._lock:
            if self._pub < 0 or self._pub == self._consumed: return None
            idx = self._pub; self._consumed = idx
        return Frame(image=self._bufs[idx], timestamp_ns=time.monotonic_ns(), source_id=self._spec.name, stream=0)
    def _loop(self):
        with mss.mss() as sct:
            t_report = time.time()
            while not self._stop.is_set():
                t0 = time.time()
                shot = sct.grab(self._mon)
                a = np.frombuffer(shot.raw, np.uint8).reshape(shot.height, shot.width, 4)
                a = a[: self._spec.height, : self._spec.width, [2, 1, 0, 3]].copy()
                a[..., 3] = 255
                idx = self._write
                self._bufs[idx].copy_(torch.from_numpy(a))
                with self._lock:
                    self._pub = idx
                self._write = (idx + 1) % 3
                self._n += 1
                if time.time() - t_report > 10:
                    print(f"[sim_view] {self._n} frames grabbed", flush=True); t_report = time.time()
                dt = self._interval - (time.time() - t0)
                if dt > 0: time.sleep(dt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default=None, help="X,Y,W,H on the display (default: the MuJoCo window)")
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--width-m", type=float, default=1.4)
    ap.add_argument("--distance", type=float, default=1.6)
    ap.add_argument("--lock", default="lazy", choices=["lazy", "head", "world"])
    a = ap.parse_args()
    region = tuple(int(v) for v in a.region.split(",")) if a.region else mujoco_region()
    print(f"[sim_view] region={region}", flush=True)

    cfg = viz.VizSessionConfig()
    cfg.mode = viz.DisplayMode.kXr
    cfg.app_name = "SonicSimView"
    cfg.xr_near_z = 0.05; cfg.xr_far_z = 100.0
    session = viz.VizSession.create(cfg)
    print(f"[sim_view] session xr={session.is_xr_mode()}", flush=True)

    src = ScreenSource("sim", region, a.fps)
    lc = viz.QuadLayerConfig(); lc.name = "sim"
    lc.resolution = viz.Resolution(src.spec.width, src.spec.height); lc.format = viz.PixelFormat.kRGBA8
    layer = session.add_quad_layer(lc)
    pc = PlacementConfig(size_meters=(a.width_m, a.width_m * src.spec.height / src.spec.width), distance=a.distance)
    placement = build_placement(a.lock, pc)

    runner = VizRunner(session, [src], [layer], [placement])
    runner.start()
    print("[sim_view] running", flush=True)
    try:
        runner.wait()
    except KeyboardInterrupt:
        runner.stop()


if __name__ == "__main__":
    main()
