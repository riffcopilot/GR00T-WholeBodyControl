import os
import queue
import sys
import threading
import time

import av
import numpy as np


_STOP = object()  # queue sentinel: the encoder thread exits when it pulls this


class VideoWriter:
    def __init__(
        self,
        output_path: str,
        width: int,
        height: int,
        fps: float,
        codec: str = "h264",
        buffer_size: int = 50,
    ):
        self.output_path = output_path
        self._first_frame = True

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Local patch: a 50-frame queue + libx264 "medium" fell behind at 640x480@50 on a loaded Jetson
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
        self._backlog_warned_at = 0.0
        # Local patch (2026-09-07): the container is touched by exactly one thread at a time. The encoder
        # thread owns it while it runs; stop()/cancel() take it over only after the thread has exited.
        # Closing it underneath a running encode (the original cancel()) segfaults inside libav — no
        # Python traceback, the whole exporter just vanishes.
        self._closed = False
        self._cancelled = False
        self._close_lock = threading.Lock()
        self._thread = threading.Thread(target=self._writer_worker, daemon=True)
        self._thread.start()

    def _assert_dimensions(self, frame: np.ndarray) -> None:
        assert (
            frame.shape[1] == self.stream.width and frame.shape[0] == self.stream.height
        ), (
            f"Incorrect frame dimensions. Input dimensions: {frame.shape[1]}x{frame.shape[0]}. "
            f"Expected dimensions: {self.stream.width}x{self.stream.height}"
        )

    def add_frame(self, frame: np.ndarray) -> None:
        if self._closed or self._cancelled:
            return  # a frame for a finished episode has nowhere to go
        self._assert_dimensions(frame)
        backlog = self.queue.qsize()
        if backlog > self.queue.maxsize // 2 and time.time() - self._backlog_warned_at > 5.0:
            self._backlog_warned_at = time.time()
            print(f"[VideoWriter] WARNING encoder falling behind: {backlog} frames queued", flush=True)
        self.queue.put(frame)

    def _encode(self, frame: np.ndarray) -> None:
        frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        if self._first_frame:
            stderr_fd = sys.stderr.fileno()
            old_stderr = os.dup(stderr_fd)
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, stderr_fd)
            try:
                packets = self.stream.encode(frame)
                for packet in packets:
                    self.container.mux(packet)
            finally:
                os.dup2(old_stderr, stderr_fd)
                os.close(old_stderr)
                os.close(devnull)
                self._first_frame = False
        else:
            packets = self.stream.encode(frame)
            for packet in packets:
                self.container.mux(packet)

    def _writer_worker(self) -> None:
        while True:
            frame = self.queue.get()
            if frame is _STOP:
                return
            if frame is None or self._cancelled:
                continue  # cancelled: drain whatever is queued without touching the container
            self._assert_dimensions(frame)
            self._encode(frame)

    def _join_worker(self, timeout: float) -> bool:
        """Ask the encoder thread to exit once it has drained the queue; True if it did."""
        self.queue.put(_STOP)
        self._thread.join(timeout=timeout)
        return not self._thread.is_alive()

    def _close_container(self) -> None:
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
            self.container.close()

    def _flush_stream(self) -> None:
        packets = self.stream.encode()
        for packet in packets:
            self.container.mux(packet)

    def stop(self) -> str:
        """Blocking call. Waits for queue to drain, flushes, and closes the container."""
        if not self.queue.empty():
            print("Waiting for video writer queue to empty...")
        # The thread encodes every queued frame, then exits on the sentinel — so by the time
        # join returns nothing else is inside the container and the flush below is the only user.
        if not self._join_worker(timeout=60.0):
            print("[VideoWriter] WARNING encoder thread still busy after 60 s; closing anyway", flush=True)
        print("Video writer queue is empty, flushing stream...")
        self._flush_stream()
        self._close_container()
        return self.output_path

    def cancel(self) -> None:
        """Immediately stops writing and deletes the output file."""
        self._cancelled = True
        # Drop the backlog so the thread reaches the sentinel at once (it skips frames anyway).
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break
        if not self._join_worker(timeout=10.0):
            print("[VideoWriter] WARNING encoder thread did not stop within 10 s; not closing the container", flush=True)
            # Leaking the container beats closing it under a live encode (that is the segfault).
            self._closed = True
        else:
            self._close_container()
        if os.path.exists(self.output_path):
            os.remove(self.output_path)

    def __del__(self) -> None:
        try:
            if not self._closed and not self._thread.is_alive():
                self._close_container()
        except Exception:
            pass
