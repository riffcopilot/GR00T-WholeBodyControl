"""Local patch: the A+B+X+Y *stop* must be held for 0.4 s (start stays instant).
A button glitch at a headset drop must not kill the policy (on the real robot that
drops the motors)."""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / "gear_sonic/scripts/pico_manager_thread_server.py"
m = p.read_text()
if "stop_request" in m:
    print("already patched"); sys.exit()
old = "            start_combo = (a_pressed) and (b_pressed) and (x_pressed) and (y_pressed)\n"
new = old + '''
            # Local patch: stop needs the combo HELD for STOP_HOLD_S; start is instant.
            if start_combo:
                if combo_down_since is None:
                    combo_down_since = time.monotonic()
            else:
                combo_down_since = None
                stop_fired = False
            stop_request = False
            if (
                start_combo
                and combo_down_since is not None
                and not stop_fired
                and time.monotonic() - combo_down_since >= STOP_HOLD_S
            ):
                stop_request = True
                stop_fired = True
'''
assert m.count(old) == 1; m = m.replace(old, new, 1)
old2 = "                if start_combo and not prev_start_combo:\n                    new_mode = StreamMode.OFF\n"
n = m.count(old2); assert n >= 4, n
m = m.replace(old2, "                if stop_request:\n                    new_mode = StreamMode.OFF\n")
old3 = "        prev_start_combo = False\n        prev_left_axis_click = False\n        while True:\n"
assert m.count(old3) == 1
m = m.replace(old3, "        prev_start_combo = False\n        prev_left_axis_click = False\n        combo_down_since = None\n        stop_fired = False\n        STOP_HOLD_S = 0.4\n        while True:\n", 1)
p.write_text(m); print("patched stop debounce;", n, "stop sites")
