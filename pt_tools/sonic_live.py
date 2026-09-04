import zmq, msgpack, numpy as np, time
s=zmq.Context().socket(zmq.SUB); s.setsockopt_string(zmq.SUBSCRIBE,"g1_debug"); s.connect("tcp://127.0.0.1:5557"); s.RCVTIMEO=2000
idx=[];dq=[];av=[];q=[]
t0=time.time()
while time.time()-t0<4:
    m=msgpack.unpackb(s.recv()[len("g1_debug"):],raw=False)
    idx.append(m["index"]); dq.append(np.abs(np.array(m["body_dq"],float)).max()); av.append(np.linalg.norm(np.array(m["base_ang_vel"],float))); q.append(np.array(m["body_q"],float).ravel())
q=np.array(q)
print(f"index {idx[0]}->{idx[-1]} ({len(idx)} msgs)  max|body_dq| mean={np.mean(dq):.3f} max={np.max(dq):.3f} rad/s  |base_ang_vel| mean={np.mean(av):.3f}")
print("body_q range over 4s (max-min):", (q.max(0)-q.min(0)).round(4).max(), " first 6 joints now:", q[-1][:6].round(3).tolist())
print("body_torso_quat:", np.array(m["body_torso_quat"],float).round(3).tolist(), " base_quat:", np.array(m["base_quat"],float).round(3).tolist())
