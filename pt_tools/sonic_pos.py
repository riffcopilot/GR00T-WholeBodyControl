import zmq, msgpack, numpy as np, time, sys
s=zmq.Context().socket(zmq.SUB); s.setsockopt_string(zmq.SUBSCRIBE,"g1_debug"); s.connect("tcp://127.0.0.1:5557"); s.RCVTIMEO=2000
dur=float(sys.argv[1]); T=[];P=[];t0=time.time()
while time.time()-t0<dur:
    m=msgpack.unpackb(s.recv()[len("g1_debug"):],raw=False)
    w,x,y,z=np.array(m["base_quat"],float).ravel(); T.append(np.degrees(np.arccos(np.clip(1-2*(x*x+y*y),-1,1)))); P.append(np.array(m["base_trans_measured"],float).ravel())
T=np.array(T);P=np.array(P)
print(f"{sys.argv[2]}: n={len(T)} tilt mean={T.mean():.1f} max={T.max():.1f}  pos start={P[0].round(3).tolist()} end={P[-1].round(3).tolist()} xy_disp={np.linalg.norm(P[-1][:2]-P[0][:2]):.3f} m z_min={P[:,2].min():.3f}")
