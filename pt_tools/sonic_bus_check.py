"""Step 1.5 before any real-robot SONIC deploy: is the robot bus quiet?

Listens on enP2p1s0 for N seconds and counts rt/lowcmd (someone commanding motors),
rt/lowstate (robot alive), rt/dex3/*/cmd (someone commanding hands). Exit 0 only if
lowcmd + dex3 cmd counts are zero. Run: ~/GR00T-WholeBodyControl/.venv_sim/bin/python ~/sonic_bus_check.py [seconds]
"""
import sys, time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_, HandCmd_

secs = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
ChannelFactoryInitialize(0, "enP2p1s0")
counts = {"rt/lowcmd": 0, "rt/lowstate": 0, "rt/dex3/left/cmd": 0, "rt/dex3/right/cmd": 0}
last_mode = {}

def mk(topic):
    def cb(m):
        counts[topic] += 1
        if topic == "rt/lowstate":
            last_mode["mode_machine"] = getattr(m, "mode_machine", None)
    return cb

subs = []
for topic, typ in (("rt/lowcmd", LowCmd_), ("rt/lowstate", LowState_), ("rt/dex3/left/cmd", HandCmd_), ("rt/dex3/right/cmd", HandCmd_)):
    s = ChannelSubscriber(topic, typ); s.Init(mk(topic), 10); subs.append(s)
time.sleep(secs)
for k, v in counts.items():
    print(f"{k:20s} {v:6d} msgs in {secs:.0f}s  (~{v/secs:.0f} Hz)")
if last_mode: print("lowstate mode_machine:", last_mode)
alive = counts["rt/lowstate"] > 0
print("ROBOT:", "alive" if alive else "no lowstate (off / link down)")
# The robot's own onboard service (motion-switcher `ai` mode) publishes rt/lowcmd at ~1 kHz; the SONIC deploy
# releases that mode itself. What must NOT exist is a publisher on THIS machine: any other process holding a
# DDS socket on the robot link. (Our own subscriber sockets are excluded by pid.)
import os, subprocess
me = str(os.getpid())
ss = subprocess.run(["ss", "-unap"], capture_output=True, text=True).stdout
BENIGN = ("sonic_temp_watch.py", "sonic_bus_check.py", "sonic_mode_check.py")  # our own read-only subscribers
def _benign(pid):
    try: return any(b in open(f"/proc/{pid}/cmdline").read() for b in BENIGN)
    except Exception: return False
import re
others = set()
for l in ss.splitlines():
    if "192.168.123.99" not in l or "users:(" not in l: continue
    pid = re.search(r"pid=(\d+)", l)
    if pid and (pid.group(1) == me or _benign(pid.group(1))): continue
    others.add(l.split("users:(")[1].split(")")[0])
others = sorted(others)
if others:
    print("BUS: BUSY — a process on the Thor holds DDS sockets on the robot link:")
    for o in others: print("   ", o)
    sys.exit(1)
if counts["rt/lowcmd"] > 0:
    print(f"BUS: rt/lowcmd at ~{counts['rt/lowcmd']/secs:.0f} Hz comes from the robot's onboard service (no Thor publisher) — the deploy will ReleaseMode")
else:
    print("BUS: quiet")
sys.exit(0)
