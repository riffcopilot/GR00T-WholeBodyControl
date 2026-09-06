"""Key relay for NVIDIA's SONIC data exporter: a persistent ZMQ PUB on tcp://*:5580 (the exporter's
ZMQKeyboardSubscriber connects there) fed by lines written to ~/sonic_keys.fifo.

Why a daemon: the exporter's SUB socket needs a stable publisher to stay connected to — a transient
publisher that binds, sends one key and exits loses the key to ZMQ's slow-joiner window.
Use ~/sonic_record.sh c|x (c = start / stop+save an episode, x = discard the one being recorded).
"""
import os, stat, sys, time
import zmq

FIFO = os.path.expanduser("~/sonic_keys.fifo")
PORT = int(os.environ.get("SONIC_KEYS_PORT", "5580"))

if not os.path.exists(FIFO) or not stat.S_ISFIFO(os.stat(FIFO).st_mode):
    if os.path.exists(FIFO):
        os.remove(FIFO)
    os.mkfifo(FIFO)

ctx = zmq.Context()
pub = ctx.socket(zmq.PUB)
pub.bind(f"tcp://*:{PORT}")
print(f"[keys] relay up: {FIFO} -> tcp://*:{PORT}", flush=True)
while True:
    with open(FIFO) as f:  # blocks until a writer opens; EOF when it closes → reopen
        for line in f:
            key = line.strip()
            if key:
                pub.send_string(key)
                print(f"[keys] {time.strftime('%H:%M:%S')} sent {key!r}", flush=True)
    time.sleep(0.05)
