# P7 resume control (2026-10-23 02:01, install = P7 build, OVSET + dynamic_mask_max_pending=0)
Trajectory md5 (first 8 hex) of offsets 0.0 s / 1.0 s (P6 run_01 / run_06). Runs kept in scratch agentN/ctrl_resume.

| seq | method | P7 resume | P6 | verdict |
|---|---|---|---|---|
| hall_t1_L3 | openvins | 8cedb817 c2d9df8f | 8cedb817 c2d9df8f | identical |
| hall_t1_L3 | savior_none (empty masks) | 8cedb817 c2d9df8f | 8cedb817 c2d9df8f | identical = openvins |
| hall_t1_L3 | yolo_naive | 7e2253b9 560f87dd | 85e477ec b160df21 | first 2186 poses identical; P7 logs 1 extra pose at shutdown |
| aisles_t1_L1 | openvins | 8004ae6f 609e5776 | 8004ae6f 609e5776 | identical |
| aisles_t1_L1 | savior_none (empty masks) | 8004ae6f 609e5776 | 8004ae6f 609e5776 | identical = openvins |
| aisles_t1_L1 | yolo_naive | ffbf9a60 e6b22472 | ffbf9a60 e6b22472 | identical |

=> P6 openvins / yolo_naive / oracle runs are reused (deterministic, 0 fallbacks in P6).
