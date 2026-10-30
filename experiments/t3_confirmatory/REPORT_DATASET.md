# t3 confirmatory split – dataset report (t3 dataset agent a9c7ff6a, saved by the coordinator 2026-10-27)
- 96 sequences (24 procedural trajectories x L0–L3; fw/sw/ms/wx x 6), all rendered, converted and checked. EXCLUSIONS.yaml: excluded [].
- DESIGN.yaml md5 bb07909870ccc6abae07f79a6473c403, frozen 2026-10-26T17:50:54Z before rendering. 5 seeds were replaced by spares under the design's own structural rule before the freeze.
- Known deviation, recorded before the freeze: moving coverage L1 0.7 % / L2 2.4 % / L3 19.8 % (t2: 1.3 / 5.9 / 18.5 %).
- Primary chain (fixed order, alpha 0.05, stop at the first failure): P1 O-Dyn+B < O-Cls+B at L2+L3; P2 SAVIOR < Y-Cls at L2+L3; P3 SAVIOR < Y-Cls at L0+L1; P4 SAVIOR < OpenVINS at L2+L3; P5 static equivalence at L0 (90 % CI within [0.90, 1.10]). Secondary S1–S14 with Holm.
- Power at n = 24: P1 1.00, P2 0.96, P3 1.00, P4 0.82, P1–P4 chain 0.79, P5 0.92 (if the true ratio is 1.00; 0.17 if it is the +8 % seen on t2).
- Checks: IMU md5 identical across levels, noise density 0.993–1.005, geometry ok. Sanity (OpenVINS + O-Dyn only): L0 0.038–0.213 m, no init failures.
- One deterministic re-render (sw03_t3_L2 hung at start-up). AMENDMENT_01: the mask-count check expected 21 files; the correct number is 20.
- Data: HDD t3/raw 125 GB, t3/ros2_stereoseg 58 GB (symlinked); GT on the NVMe.
- run_t3.sh steps: check ov2 ov2_eval ov2_audit vins vins_eval analyze. Rough cost: ~19 h OV2 family (3360 runs) + ~15 h VINS.
