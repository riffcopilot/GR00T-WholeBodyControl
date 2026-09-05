import sys, pathlib
p = pathlib.Path(sys.argv[1]) / "gear_sonic/scripts/pico_manager_thread_server.py"
m = p.read_text()
if "combo_press_mode" in m:
    print("already patched v2"); sys.exit()
old = """            if start_combo:
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
"""
new = """            if start_combo:
                if combo_down_since is None:
                    combo_down_since = time.monotonic()
                    combo_press_mode = current_mode  # mode when this press began
            else:
                combo_down_since = None
                stop_fired = False
            stop_request = False
            if (
                start_combo
                and combo_down_since is not None
                and combo_press_mode != StreamMode.OFF  # a press that started the policy can't also stop it
                and not stop_fired
                and time.monotonic() - combo_down_since >= STOP_HOLD_S
            ):
"""
assert old in m; m = m.replace(old, new, 1)
old2 = "        combo_down_since = None\n        stop_fired = False\n        STOP_HOLD_S = 0.4\n"
assert old2 in m; m = m.replace(old2, old2 + "        combo_press_mode = StreamMode.OFF\n", 1)
p.write_text(m); print("patched v2")
