import sys, pathlib
p = pathlib.Path(sys.argv[1]) / "gear_sonic/scripts/pico_manager_thread_server.py"
m = p.read_text()
if "[PlannerLoop] axes" in m:
    print("already patched"); sys.exit()
old = "            lx, ly, rx, ry = get_controller_axes(self.reader)\n"
new = old + '''            # Local patch: 1 Hz input telemetry so a dead stick is visible in the log
            _now = time.monotonic()
            if _now - getattr(self, "_axes_log_t", 0.0) >= 1.0:
                self._axes_log_t = _now
                print(f"[PlannerLoop] axes L=({lx:+.2f},{ly:+.2f}) R=({rx:+.2f},{ry:+.2f}) gait={self.mode.name} stream={stream_mode.name}", flush=True)
'''
assert m.count(old) == 1; m = m.replace(old, new, 1)
p.write_text(m); print("patched axes debug")
