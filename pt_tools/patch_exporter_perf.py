"""Local patches (Physical Turing, 2026-09-06) to NVIDIA's SONIC data exporter for a loaded Jetson Thor:
1. video_writer.py: libx264 ultrafast/zerolatency (default preset could not sustain 640x480@50 on the loaded Thor:
   the encoder thread fell behind, the 50-frame queue filled and add_frame blocked ~35 ms → ~32 Hz real rate while
   timestamps claimed 50 Hz); bigger queue; a backpressure warning when the queue is half full.
2. run_data_exporter.py: drain up to 400 streamer messages per loop and RCVHWM 400 (was 20/20): the one-tick
   grip-combo toggles in manager_state were dropped when the queue overflowed.
3. text_to_speech.py: fall back to SONIC_SAY_CMD (a shell command receiving the message) when pyttsx3/espeak is
   unavailable — used to play cues through the G1's speaker.
"""
import pathlib, re
R = pathlib.Path.home() / "GR00T-WholeBodyControl"

p = R / "gear_sonic/data/video_writer.py"; s = p.read_text()
if "ultrafast" not in s:
    old = '''        self.queue = queue.Queue(maxsize=buffer_size)
        self.container = av.open(output_path, mode="w")
        self.stream = self.container.add_stream(codec, rate=fps)
        self.stream.width = width
        self.stream.height = height'''
    new = '''        # Local patch: a 50-frame queue + libx264 "medium" fell behind at 640x480@50 on a loaded Jetson
        # (add_frame blocked on queue.put → the exporter loop ran ~32 Hz while stamping 50). Fast preset,
        # zero-latency tuning, a deeper queue, and a loud warning when the encoder is falling behind.
        self.queue = queue.Queue(maxsize=max(buffer_size, 400))
        self.container = av.open(output_path, mode="w")
        enc_options = {"preset": "ultrafast", "tune": "zerolatency", "crf": "23"} if codec in ("h264", "libx264") else {}
        self.stream = self.container.add_stream(codec, rate=fps, options=enc_options)
        self.stream.width = width
        self.stream.height = height
        try:
            self.stream.pix_fmt = "yuv420p"
            self.stream.thread_type = "AUTO"
        except Exception:
            pass
        self._backlog_warned_at = 0.0'''
    assert old in s, "video_writer anchor"; s = s.replace(old, new, 1)
    old = '''    def add_frame(self, frame: np.ndarray) -> None:
        self._assert_dimensions(frame)
        self.queue.put(frame)'''
    new = '''    def add_frame(self, frame: np.ndarray) -> None:
        self._assert_dimensions(frame)
        backlog = self.queue.qsize()
        if backlog > self.queue.maxsize // 2 and time.time() - self._backlog_warned_at > 5.0:
            self._backlog_warned_at = time.time()
            print(f"[VideoWriter] WARNING encoder falling behind: {backlog} frames queued", flush=True)
        self.queue.put(frame)'''
    assert old in s, "add_frame anchor"; s = s.replace(old, new, 1)
    p.write_text(s); print("video_writer patched")
else:
    print("video_writer already patched")

p = R / "gear_sonic/scripts/run_data_exporter.py"; s = p.read_text()
if "max_polls = 400" not in s:
    s2, n1 = re.subn(r"self\._sonic_zmq_socket\.setsockopt\(zmq\.RCVHWM, 20\)", "self._sonic_zmq_socket.setsockopt(zmq.RCVHWM, 400)  # local patch: was 20 — grip-combo toggles were dropped on overflow", s)
    s2, n2 = re.subn(r"        max_polls = 20\n", "        max_polls = 400  # local patch: drain everything queued each loop (was 20)\n", s2)
    assert n1 == 1 and n2 == 1, (n1, n2)
    p.write_text(s2); print("exporter drain patched")
else:
    print("exporter already patched")

p = R / "gear_sonic/utils/data_collection/text_to_speech.py"; s = p.read_text()
if "SONIC_SAY_CMD" not in s:
    old = '''        except Exception as e:
            print(f"[Text To Speech] Initialization failed: {e}")
            self.engine = None'''
    new = '''        except Exception as e:
            print(f"[Text To Speech] Initialization failed: {e}")
            self.engine = None
        # Local patch: no espeak on the Thor — route cues to a shell command (the G1's own speaker).
        import os, shlex, subprocess
        self._say_cmd = os.environ.get("SONIC_SAY_CMD")
        if self.engine is None and self._say_cmd:
            self._subprocess, self._shlex = subprocess, shlex
            self.engine = "cmd"
            print(f"[Text To Speech] using SONIC_SAY_CMD={self._say_cmd}")'''
    assert old in s, "tts init anchor"; s = s.replace(old, new, 1)
    old = '''    def _say_blocking(self, message: str):
        with self._lock:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except RuntimeError:
                pass'''
    new = '''    def _say_blocking(self, message: str):
        with self._lock:
            if self.engine == "cmd":
                try:
                    self._subprocess.run(self._shlex.split(self._say_cmd) + [message], timeout=8,
                                         stdout=self._subprocess.DEVNULL, stderr=self._subprocess.DEVNULL)
                except Exception as e:
                    print(f"[Text To Speech] say command failed: {e}")
                return
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except RuntimeError:
                pass'''
    assert old in s, "tts say anchor"; s = s.replace(old, new, 1)
    p.write_text(s); print("tts patched")
else:
    print("tts already patched")
