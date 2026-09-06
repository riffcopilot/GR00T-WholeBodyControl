import os
import queue
import sys
import threading
import time

import av
import numpy as np


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
        thread = threading.Thread(target=self._writer_worker, daemon=True)
        thread.start()

    def _assert_dimensions(self, frame: np.ndarray) -> None:
        assert (
            frame.shape[1] == self.stream.width and frame.shape[0] == self.stream.height
        ), (
            f"Incorrect frame dimensions. Input dimensions: {frame.shape[1]}x{frame.shape[0]}. "
            f"Expected dimensions: {self.stream.width}x{self.stream.height}"
        )

    def add_frame(self, frame: np.ndarray) -> None:
        self._assert_dimensions(frame)
        backlog = self.queue.qsize()
        if backlog > self.queue.maxsize // 2 and time.time() - self._backlog_warned_at > 5.0:
            self._backlog_warned_at = time.time()
            print(f"[VideoWriter] WARNING encoder falling behind: {backlog} frames queued", flush=True)
        self.queue.put(frame)

    def _writer_worker(self) -> None:
        while True:
            frame = self.queue.get()
            if frame is None:
                continue
            self._assert_dimensions(frame)
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

    def _flush_stream(self) -> None:
        packets = self.stream.encode()
        for packet in packets:
            self.container.mux(packet)

    def stop(self) -> str:
        """Blocking call. Waits for queue to drain, flushes, and closes the container."""
        if not self.queue.empty():
            print("Waiting for video writer queue to empty...")
            while not self.queue.empty():
                time.sleep(0.1)

        print("Video writer queue is empty, flushing stream...")
        self._flush_stream()
        self.container.close()
        return self.output_path

    def cancel(self) -> None:
        """Immediately stops writing and deletes the output file."""
        if os.path.exists(self.output_path):
            os.remove(self.output_path)
        self.container.close()

    def __del__(self) -> None:
        self.container.close()
