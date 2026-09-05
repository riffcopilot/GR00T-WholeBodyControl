"""Ask the G1's motion switcher which onboard mode is active (empty = released)."""
import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
ChannelFactoryInitialize(0, "enP2p1s0")
try:
    from unitree_sdk2py.b2.motion_switcher.motion_switcher_client import MotionSwitcherClient
except ImportError:
    from unitree_sdk2py.go2.motion_switcher.motion_switcher_client import MotionSwitcherClient  # older layouts
msc = MotionSwitcherClient(); msc.SetTimeout(3.0); msc.Init()
code, result = msc.CheckMode()
print("CheckMode code:", code, "result:", result)
