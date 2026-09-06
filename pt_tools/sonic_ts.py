"""Line stamper: prefixes every stdin line with the unix time (ms) so the exporter's event lines
("Started recording N", "Stopping recording", "Finished saving episode", "Discarded episode") carry
wall-clock instants — the LeRobot dataset itself stamps frames by index only, and the offload rig
needs real start/end times per episode. Usage: producer | python3 -u sonic_ts.py | tee log"""
import sys, time
for line in sys.stdin:
    sys.stdout.write("%.3f %s" % (time.time(), line))
    sys.stdout.flush()
