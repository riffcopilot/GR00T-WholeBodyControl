import zmq, msgpack, numpy as np, time, sys
s = zmq.Context().socket(zmq.SUB); s.setsockopt_string(zmq.SUBSCRIBE,"g1_debug"); s.connect("tcp://127.0.0.1:5557"); s.RCVTIMEO=2000
T=[];Z=[];t0=time.time()
while time.time()-t0<8:
    try: raw=s.recv()
    except zmq.Again: print("no messages"); sys.exit(1)
    m=msgpack.unpackb(raw[len("g1_debug"):],raw=False)
    w,x,y,z=np.array(m["base_quat"],float).ravel(); T.append(np.degrees(np.arccos(np.clip(1-2*(x*x+y*y),-1,1))))
    Z.append(np.array(m["base_trans_measured"],float).ravel())
T=np.array(T);Z=np.array(Z)
print(f"n={len(T)} tilt mean={T.mean():.1f} std={T.std():.1f} max={T.max():.1f} deg")
print(f"base_trans_measured xyz mean={Z.mean(axis=0).round(3).tolist()} z min={Z[:,2].min():.3f} z max={Z[:,2].max():.3f}")
