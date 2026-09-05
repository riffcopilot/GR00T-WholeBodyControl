import os; os.environ.setdefault("MUJOCO_GL","egl")
import mujoco, numpy as np

m = mujoco.MjModel.from_xml_path("gear_sonic/data/assets/robot_description/mjcf/g1_29dof_rev_1_0.xml")
d = mujoco.MjData(m)
mujoco.mj_resetData(m, d)
# all actuated joints at 0 (free base keeps its default quaternion); place pelvis at standing height
if m.nq >= 7 and m.jnt_type[0] == mujoco.mjtJoint.mjJNT_FREE:
    d.qpos[:] = 0; d.qpos[2] = 0.79; d.qpos[3] = 1.0
else:
    d.qpos[:] = 0
mujoco.mj_forward(m, d)
m.vis.global_.offwidth = 1400; m.vis.global_.offheight = 1000
r = mujoco.Renderer(m, height=900, width=700)
cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
cam.lookat[:] = [0, 0, 0.75]; cam.distance = 2.6; cam.elevation = -8
imgs = []
for name, az in [("front", 180), ("side", 90), ("three_quarter", 135)]:
    cam.azimuth = az; r.update_scene(d, cam); imgs.append(r.render().copy())
img=np.concatenate(imgs, axis=1); open(os.path.expanduser("~/g1_reference_pose.ppm"),"wb").write(b"P6 %d %d 255\n" % (img.shape[1], img.shape[0]) + img.astype(np.uint8).tobytes())
print("saved", m.nq)
