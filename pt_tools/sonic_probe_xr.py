"""Second OpenXR session on the running CloudXR runtime: report what the headset actually streams."""
import os, time, sys
for line in open(os.path.expanduser("~/.cloudxr/run/cloudxr.env")):
    line = line.strip()
    if line.startswith("export "):
        k, v = line[7:].split("=", 1); os.environ[k] = v
import isaacteleop.deviceio as deviceio, isaacteleop.oxr as oxr
head = deviceio.HeadTracker(); ctrl = deviceio.ControllerTracker(); body = deviceio.FullBodyTrackerPico()
trackers = [head, ctrl, body]
ext = deviceio.DeviceIOSession.get_required_extensions(trackers)
print("required ext:", ext, flush=True)
with oxr.OpenXRSession("SonicProbe", ext) as s:
    with deviceio.DeviceIOSession.run(trackers, s.get_handles()) as sess:
        for i in range(int(sys.argv[1]) if len(sys.argv) > 1 else 40):
            sess.update()
            hd = head.get_head(sess).data
            lc = ctrl.get_left_controller(sess).data; rc = ctrl.get_right_controller(sess).data
            b = body.get_body_pose(sess).data
            if i == 0:
                print("body attrs:", [a for a in dir(b) if not a.startswith("_")], flush=True)
            def pv(p):
                try: return (p.is_valid, round(p.pose.position.x,3), round(p.pose.position.y,3), round(p.pose.position.z,3))
                except Exception as e: return f"n/a {e}"
            def cv(c):
                if c is None: return None
                ap = c.aim_pose; ins = c.inputs
                return (pv(ap) if ap is not None else None, None if ins is None else (round(ins.trigger_value,2), ins.primary_click, ins.secondary_click, round(ins.thumbstick_x,2), round(ins.thumbstick_y,2)))
            nvalid = 0
            try:
                for j in range(24):
                    jt = b.joints.joints(j)
                    if jt is not None and getattr(jt, "is_valid", False): nvalid += 1
            except Exception as e:
                nvalid = f"err {e}"
            tracked = getattr(b, "all_joint_poses_tracked", "?")
            if i % 5 == 0:
                print(f"[{i}] head={pv(hd)} L={cv(lc)} R={cv(rc)} body_valid_joints={nvalid} all_tracked={tracked}", flush=True)
            time.sleep(0.1)
