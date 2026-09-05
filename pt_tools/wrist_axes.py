import re, sys, numpy as np
from scipy.spatial.transform import Rotation as R
side = sys.argv[2] if len(sys.argv) > 2 else "L"
rows = []
for l in open(sys.argv[1]):
    m = re.search(side + r" pos=\[([^\]]*)\] rpy=\[([^\]]*)\]", l)
    if not m: continue
    pos = np.array([float(x) for x in m.group(1).split()])
    rpy = np.array([float(x.rstrip(".")) for x in m.group(2).split()])
    rows.append((pos, rpy))
print(len(rows), "samples for", side)
R0 = R.from_euler("xyz", rows[0][1], degrees=True)
print("relative rotation vs first sample, in the wrist's own frame (rotvec deg) | position delta (m)")
for pos, rpy in rows[1:]:
    rel = (R0.inv() * R.from_euler("xyz", rpy, degrees=True)).as_rotvec(degrees=True)
    ax = "xyz"[int(np.abs(rel).argmax())]
    print(f"  rot {np.round(rel, 0)}  dominant {ax}  dpos {np.round(pos - rows[0][0], 2)}")
