"""Log the hottest motors (driver + winding temps, torque) every 2 s while the robot is under control."""
import time, sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
names = ["L_hip_pitch","L_hip_roll","L_hip_yaw","L_knee","L_ankle_pitch","L_ankle_roll","R_hip_pitch","R_hip_roll","R_hip_yaw","R_knee","R_ankle_pitch","R_ankle_roll","waist_yaw","waist_roll","waist_pitch","L_sh_pitch","L_sh_roll","L_sh_yaw","L_elbow","L_wr_roll","L_wr_pitch","L_wr_yaw","R_sh_pitch","R_sh_roll","R_sh_yaw","R_elbow","R_wr_roll","R_wr_pitch","R_wr_yaw"]
ChannelFactoryInitialize(0, "enP2p1s0")
st = {}
s = ChannelSubscriber("rt/lowstate", LowState_); s.Init(lambda m: st.__setitem__("m", m), 10)
while True:
    time.sleep(2)
    m = st.get("m")
    if m is None:
        print(time.strftime("%H:%M:%S"), "no lowstate", flush=True); continue
    rows = []
    for i, n in enumerate(names):
        ms = m.motor_state[i]
        rows.append((max(ms.temperature[0], ms.temperature[1]), n, ms.temperature[0], ms.temperature[1], round(ms.tau_est, 1), ms.motorstate))
    rows.sort(reverse=True)
    errs = [n for (_, n, _, _, _, s_) in rows if s_ != 0]
    top = "  ".join(f"{n}:{tm}/{td}C {tau}Nm" for (_, n, tm, td, tau, _) in rows[:4])
    flag = "  !!! >=90" if rows[0][0] >= 90 else ""
    print(time.strftime("%H:%M:%S"), top, ("  MOTORSTATE!=0: " + ",".join(errs)) if errs else "", flag, flush=True)
