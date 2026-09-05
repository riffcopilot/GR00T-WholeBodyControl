import zmq, msgpack, numpy as np, time, sys
ctx = zmq.Context(); s = ctx.socket(zmq.SUB); s.setsockopt_string(zmq.SUBSCRIBE, "g1_debug"); s.connect("tcp://127.0.0.1:5557")
s.RCVTIMEO = 2000
tilts=[]; qs=[]; t0=time.time(); n=0
while time.time()-t0 < 8:
    try: raw = s.recv()
    except zmq.Again: print("no messages"); sys.exit(1)
    m = msgpack.unpackb(raw[len("g1_debug"):], raw=False); n+=1
    q = np.array(m["base_quat"], dtype=float).ravel()
    # try both wxyz and xyzw: gravity direction in body frame tilt = angle between body z and world z
    for order in ("wxyz","xyzw"):
        w,x,y,z = (q if order=="wxyz" else (q[3],q[0],q[1],q[2]))
        # world z axis expressed via rotation of body z: R[2,2] = 1-2(x^2+y^2)
        r22 = 1-2*(x*x+y*y)
        if order=="wxyz": tw=np.degrees(np.arccos(np.clip(r22,-1,1)))
        else: tx=np.degrees(np.arccos(np.clip(r22,-1,1)))
    tilts.append((tw,tx)); qs.append(np.array(m["body_q"],dtype=float).ravel())
tilts=np.array(tilts); qs=np.array(qs)
print(f"msgs={n} rate={n/8:.0f}Hz")
print(f"tilt(wxyz) mean={tilts[:,0].mean():.1f} std={tilts[:,0].std():.1f} max={tilts[:,0].max():.1f} deg")
print(f"tilt(xyzw) mean={tilts[:,1].mean():.1f} std={tilts[:,1].std():.1f} max={tilts[:,1].max():.1f} deg")
print(f"body_q dims={qs.shape[1]} leg joint std (first 12) = {qs[:,:12].std(axis=0).round(3).tolist()}")
print("keys:", [k for k in m.keys()][:25])
