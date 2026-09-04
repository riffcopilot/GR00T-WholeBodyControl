import sys, pathlib
p = pathlib.Path(sys.argv[1]) / "gear_sonic/scripts/pico_manager_thread_server.py"
m = p.read_text()
if "[PlannerLoop] wrist" in m:
    print("already patched"); sys.exit()
old = """                    vr_3pt_pose = self.three_point.process_smpl_pose(sample["body_poses_np"])
                    vr_3pt_position = (vr_3pt_pose[:, :3].flatten()).tolist()
"""
new = """                    vr_3pt_pose = self.three_point.process_smpl_pose(sample["body_poses_np"])
                    # Local patch: 1 Hz calibrated wrist readout (robot frame, deg) to verify the axis mapping
                    _nw = time.monotonic()
                    if _nw - getattr(self, "_wrist_log_t", 0.0) >= 1.0:
                        self._wrist_log_t = _nw
                        _e = lambda q: np.round(sRot.from_quat(q, scalar_first=True).as_euler("xyz", degrees=True), 0)
                        print(f"[PlannerLoop] wrist L pos={np.round(vr_3pt_pose[0,:3],2)} rpy={_e(vr_3pt_pose[0,3:])} | R pos={np.round(vr_3pt_pose[1,:3],2)} rpy={_e(vr_3pt_pose[1,3:])} | hand-frame={getattr(self.three_point,'body_frame_wrist_offset',None)}", flush=True)
                    vr_3pt_position = (vr_3pt_pose[:, :3].flatten()).tolist()
"""
assert m.count(old) == 1; m = m.replace(old, new, 1)
p.write_text(m); print("patched wrist debug")
