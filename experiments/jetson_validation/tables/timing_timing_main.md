# Jetson Orin NX 8 GB timing (timing_main): median / p90 / p99 ms, rate 1.0 (20 Hz stereo, real time)

power mode MAXN, jetson_clocks on, GPU [765000000, 765000000, 765000000], other containers: 'none'

Stages per camera frame (savior_node) or per OpenVINS update. classification = motion evidence + interaction gating + tracker (+ band); convert/publish = node_total - convert - segment - pipeline total (ROS conversion, mask publish, callback overhead); OV update = OV total - OV front-end (propagation, MSCKF / SLAM update, marginalisation); mask latency = image -> mask receive, end-to-end = image -> OpenVINS pose receive (latency probe, same machine clock).

| method | runs | segmentation | depth | classification (motion+gating+tracking) | mask compose | convert/publish | savior_node total | OV front-end | OV update | OV total | mask latency | end-to-end latency |
|---|--:|---|---|---|---|---|---|---|---|---|---|---|
| OpenVINS | 4 | - | - | - | - | - | - | 4.1 / 5.1 / 6.3 | 4.5 / 7.2 / 14.9 | 8.9 / 11.6 / 19.0 | - | 14.2 / 18.1 / 77.8 |
| Y-Cls | 4 | 24.2 / 50.1 / 84.6 | 19.8 / 43.1 / 72.8 | 0.4 / 1.3 / 2.8 | 6.7 / 21.2 / 38.9 | 1.8 / 2.9 / 4.1 | 51.8 / 118.8 / 205.1 | 4.3 / 5.4 / 6.9 | 5.3 / 8.2 / 16.3 | 9.7 / 12.9 / 20.9 | 490.4 / 595.2 / 681.7 | 30025.3 / 30304.2 / 31637.0 |
| SAVIOR (Py) | 4 | 33.6 / 67.1 / 99.3 | 28.3 / 57.4 / 80.8 | 35.0 / 76.9 / 110.1 | 4.5 / 11.3 / 19.2 | 2.4 / 4.2 / 5.6 | 108.6 / 211.0 / 298.3 | 4.4 / 5.5 / 8.2 | 4.8 / 7.8 / 15.0 | 9.4 / 12.7 / 20.4 | 10070.0 / 22865.7 / 37881.1 | 30021.9 / 30360.0 / 34168.9 |
| SAVIOR (C++) | 4 | 9.5 / 13.5 / 16.1 | 6.4 / 9.6 / 11.9 | 6.5 / 14.1 / 20.0 | 0.8 / 1.5 / 2.1 | 1.0 / 1.2 / 1.8 | 24.5 / 39.5 / 49.1 | 4.3 / 5.1 / 7.1 | 4.9 / 7.8 / 13.6 | 9.4 / 12.6 / 18.4 | 24.9 / 42.4 / 97.9 | 37.8 / 57.6 / 109.7 |
| SAVIOR-edge (Py) | 4 | 32.1 / 62.0 / 97.2 | 27.5 / 56.2 / 79.4 | 35.8 / 76.9 / 109.5 | 4.4 / 10.9 / 17.5 | 2.5 / 4.1 / 5.4 | 105.7 / 203.7 / 290.6 | 4.4 / 5.7 / 7.6 | 5.1 / 8.0 / 16.1 | 9.8 / 12.9 / 21.3 | 9551.9 / 22167.2 / 36584.7 | 30030.1 / 30359.1 / 33917.9 |
| SAVIOR-edge (C++) | 4 | 6.9 / 10.7 / 13.1 | 6.5 / 10.1 / 12.7 | 6.7 / 14.9 / 21.2 | 0.8 / 1.6 / 2.3 | 1.0 / 1.2 / 2.1 | 22.1 / 37.6 / 48.2 | 4.4 / 5.6 / 7.0 | 4.6 / 7.6 / 13.9 | 9.4 / 12.3 / 18.6 | 22.6 / 40.7 / 95.7 | 39.6 / 30014.4 / 30166.3 |

## Per sequence (savior_node total, OV total, end-to-end)

| method | seq | frames | node_total | OV total | mask latency | end-to-end |
|---|---|--:|---|---|---|---|
| OpenVINS | hall_t1_L3 | 4367 | - | 8.1 / 9.5 / 11.0 | - | 13.4 / 15.4 / 113.0 |
| OpenVINS | aisles_t1_L2 | 4206 | - | 10.0 / 13.0 / 21.8 | - | 15.3 / 19.5 / 67.3 |
| Y-Cls | hall_t1_L3 | 3753 | 48.2 / 87.6 / 140.5 | 9.4 / 12.3 / 17.8 | 293.1 / 565.8 / 618.5 | 30019.2 / 30221.7 / 31424.0 |
| Y-Cls | aisles_t1_L2 | 2559 | 63.0 / 158.5 / 219.7 | 10.1 / 13.6 / 21.9 | 539.4 / 637.8 / 702.2 | 30032.4 / 30418.9 / 31822.7 |
| SAVIOR (Py) | hall_t1_L3 | 2116 | 91.7 / 177.2 / 239.7 | 8.8 / 11.4 / 16.4 | 8783.6 / 18939.4 / 22209.1 | 30017.7 / 30169.5 / 31218.0 |
| SAVIOR (Py) | aisles_t1_L2 | 1484 | 129.6 / 240.7 / 316.4 | 10.2 / 13.6 / 22.3 | 11861.5 / 32349.1 / 38976.8 | 30027.3 / 31174.9 / 34643.3 |
| SAVIOR (C++) | hall_t1_L3 | 4504 | 23.6 / 31.4 / 37.7 | 8.7 / 11.1 / 14.8 | 24.0 / 32.2 / 86.8 | 35.7 / 43.5 / 78.9 |
| SAVIOR (C++) | aisles_t1_L2 | 4340 | 27.0 / 44.3 / 50.2 | 10.4 / 13.6 / 20.1 | 27.7 / 51.9 / 100.0 | 41.6 / 69.0 / 115.1 |
| SAVIOR-edge (Py) | hall_t1_L3 | 2227 | 88.1 / 167.3 / 206.5 | 9.5 / 12.3 / 18.5 | 8269.5 / 17933.6 / 22069.6 | 30029.9 / 30219.7 / 30787.6 |
| SAVIOR-edge (Py) | aisles_t1_L2 | 1507 | 125.7 / 248.1 / 304.4 | 10.1 / 13.5 / 23.2 | 11389.7 / 31614.7 / 38220.8 | 30030.4 / 30871.1 / 34413.7 |
| SAVIOR-edge (C++) | hall_t1_L3 | 4503 | 21.3 / 28.9 / 35.2 | 8.7 / 10.6 / 13.8 | 21.7 / 29.9 / 74.5 | 39.3 / 30017.9 / 30293.6 |
| SAVIOR-edge (C++) | aisles_t1_L2 | 4340 | 24.5 / 43.1 / 49.5 | 10.1 / 13.4 / 20.2 | 25.2 / 47.6 / 97.4 | 39.8 / 64.3 / 113.4 |

## Does the filter keep up? (per run)

| method | seq | run | status | images (probe) | savior frames | masks (probe) | OV meas. | exact | fallback latest+empty | late | too_late | n_in_core | hold avg / max ms | poses (OpenVINS-alone) | backlog at end s | mask lat. >50 / >100 / >250 ms |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|---|--:|---|
| OpenVINS | aisles_t1_L2 | run_01 | ok/0 | 2174 | - | - | - | - | - | - | - | 0 | - / - | 2103 (2103) | -0.034 | - |
| OpenVINS | aisles_t1_L2 | run_02 | ok/0 | 2164 | - | - | - | - | - | - | - | 0 | - / - | 2103 (2103) | -0.035 | - |
| OpenVINS | hall_t1_L3 | run_01 | ok/0 | 2258 | - | - | - | - | - | - | - | 0 | - / - | 2185 (2185) | 0.013 | - |
| OpenVINS | hall_t1_L3 | run_02 | ok/0 | 2246 | - | - | - | - | - | - | - | 0 | - / - | 2182 (2182) | -0.187 | - |
| Y-Cls | aisles_t1_L2 | run_01 | ok/0 | 2176 | 1285 | 1283 | 1643 | 8 | 3278 | 0 | - | 0 | 29942.5 / 30563.6 | 1511 (2103) | 0.407 | 1036 / 1019 / 996 |
| Y-Cls | aisles_t1_L2 | run_02 | ok/0 | 2160 | 1274 | 1272 | 1631 | 8 | 3254 | 0 | - | 0 | 29935.3 / 30169.9 | 1502 (2103) | -0.035 | 1017 / 1002 / 982 |
| Y-Cls | hall_t1_L3 | run_01 | ok/0 | 2256 | 1879 | 1879 | 1715 | 2 | 3428 | 0 | - | 0 | 29993.0 / 30277.6 | 1587 (2185) | 0.098 | 1427 / 1231 / 1008 |
| Y-Cls | hall_t1_L3 | run_02 | ok/0 | 2244 | 1874 | 1872 | 1713 | 6 | 3420 | 0 | - | 0 | 29955.2 / 30215.6 | 1590 (2182) | 0.217 | 1438 / 1230 / 995 |
| SAVIOR (Py) | aisles_t1_L2 | run_01 | ok/0 | 2176 | 735 | 735 | 1643 | 839 | 2447 | 119 | - | 0 | 28897.5 / 30664.6 | 1497 (2103) | -0.211 | 735 / 735 / 734 |
| SAVIOR (Py) | aisles_t1_L2 | run_02 | ok/0 | 2162 | 749 | 749 | 1632 | 956 | 2308 | 192 | - | 0 | 26431.7 / 30861.2 | 1497 (2103) | -0.213 | 749 / 749 / 748 |
| SAVIOR (Py) | hall_t1_L3 | run_01 | ok/0 | 2254 | 1042 | 1040 | 1884 | 1376 | 2392 | 0 | - | 0 | 26547.9 / 30127.2 | 1587 (2185) | 0.085 | 1038 / 1038 / 1037 |
| SAVIOR (Py) | hall_t1_L3 | run_02 | ok/0 | 2244 | 1074 | 1074 | 1873 | 1242 | 2504 | 0 | - | 0 | 28339.6 / 30285.1 | 1590 (2182) | 0.236 | 1074 / 1074 / 1073 |
| SAVIOR (C++) | aisles_t1_L2 | run_01 | ok/0 | 2176 | 2176 | 2176 | 2176 | 4352 | 0 | 0 | - | 0 | 29.7 / 177.1 | 2103 (2103) | -0.025 | 248 / 31 / 0 |
| SAVIOR (C++) | aisles_t1_L2 | run_02 | ok/0 | 2164 | 2164 | 2164 | 2164 | 4328 | 0 | 0 | - | 0 | 29.1 / 247.5 | 2103 (2103) | -0.027 | 227 / 13 / 0 |
| SAVIOR (C++) | hall_t1_L3 | run_01 | ok/0 | 2258 | 2258 | 2258 | 2258 | 4516 | 0 | 0 | - | 0 | 25.1 / 245.3 | 2186 (2185) | 0.03 | 46 / 17 / 1 |
| SAVIOR (C++) | hall_t1_L3 | run_02 | ok/0 | 2243 | 2246 | 2246 | 2246 | 4492 | 0 | 0 | - | 0 | 25.7 / 266.9 | 2184 (2182) | -0.066 | 58 / 16 / 2 |
| SAVIOR-edge (Py) | aisles_t1_L2 | run_01 | ok/0 | 2174 | 755 | 755 | 1643 | 992 | 2294 | 114 | 0 | 0 | 26172.4 / 30504.5 | 1504 (2103) | 0.103 | 753 / 753 / 752 |
| SAVIOR-edge (Py) | aisles_t1_L2 | run_02 | ok/0 | 2160 | 752 | 750 | 1590 | 982 | 2198 | 186 | 0 | 0 | 26149.4 / 30670.1 | 1507 (2103) | 0.262 | 748 / 748 / 747 |
| SAVIOR-edge (Py) | hall_t1_L3 | run_01 | ok/0 | 2254 | 1116 | 1114 | 1898 | 1244 | 2552 | 0 | 0 | 0 | 26810.5 / 30255.1 | 1591 (2185) | 0.292 | 1110 / 1110 / 1109 |
| SAVIOR-edge (Py) | hall_t1_L3 | run_02 | ok/0 | 2239 | 1111 | 1107 | 1887 | 1248 | 2526 | 0 | 0 | 0 | 26733.2 / 30177.8 | 1584 (2182) | -0.002 | 1102 / 1102 / 1101 |
| SAVIOR-edge (C++) | aisles_t1_L2 | run_01 | ok/0 | 2176 | 2176 | 2176 | 2176 | 4352 | 0 | 0 | 0 | 0 | 27.5 / 216.7 | 2103 (2103) | -0.024 | 199 / 17 / 0 |
| SAVIOR-edge (C++) | aisles_t1_L2 | run_02 | ok/0 | 2164 | 2164 | 2164 | 2164 | 4328 | 0 | 0 | 0 | 0 | 26.9 / 150.0 | 2103 (2103) | -0.031 | 191 / 20 / 0 |
| SAVIOR-edge (C++) | hall_t1_L3 | run_01 | ok/0 | 2258 | 2257 | 2257 | 1725 | 2 | 3448 | 0 | 0 | 0 | 29986.6 / 30100.4 | 1587 (2185) | 0.063 | 46 / 25 / 13 |
| SAVIOR-edge (C++) | hall_t1_L3 | run_02 | ok/0 | 2242 | 2246 | 2246 | 2246 | 4492 | 0 | 0 | 0 | 0 | 22.0 / 215.8 | 2186 (2182) | 0.028 | 21 / 9 / 0 |

## Resources (tegrastats 5 Hz over the bag playback, worst / mean over the runs of a method)

Idle baseline (container up, nothing running, 30 s): RAM 2099 MB, VDD_IN 7333 mW, CPU 0.3 %, GR3D 0.0 %.

| method | RAM used max MB (system) | swap growth MB | min MemAvailable MB | GR3D (GPU) mean / p95 % | CPU mean % (6 cores) | VDD_IN mean / p95 mW | VDD_CPU_GPU_CV mean mW | VDD_SOC mean mW | energy / frame mJ (VDD_IN) | above idle mJ / frame | T max C | peak RSS per process MB |
|---|--:|--:|--:|---|--:|---|--:|--:|--:|--:|--:|---|
| OpenVINS | 2398 | 5 | 5267 | 0.0 / 0 | 12.2 | 8111 / 8338 | 2281 | 2583 | 406 | 39 | 52.3 | ros2_bag_play 149, run_subscribe_msckf 97, latprobe.py 48, pose_recorder 44 |
| Y-Cls | 4210 | 1 | 3447 | 27.2 / 97 | 28.3 | 11836 / 12776 | 4922 | 3017 | 592 | 225 | 55.7 | savior_node 1245, run_subscribe_msckf 937, ros2_bag_play 146, latprobe.py 50 |
| SAVIOR (Py) | 4272 | 2 | 3384 | 22.5 / 97 | 38.0 | 11478 / 12380 | 4720 | 2942 | 574 | 207 | 56.0 | savior_node 1359, run_subscribe_msckf 880, ros2_bag_play 148, latprobe.py 49 |
| SAVIOR (C++) | 2793 | 0 | 4889 | 16.6 / 54 | 26.3 | 10928 / 12102 | 4312 | 2906 | 546 | 180 | 55.5 | savior_node 462, ros2_bag_play 147, run_subscribe_msckf 105, latprobe.py 49 |
| SAVIOR-edge (Py) | 4510 | 1 | 3140 | 19.2 / 89 | 38.3 | 11201 / 12102 | 4519 | 2904 | 560 | 193 | 55.8 | savior_node 1333, run_subscribe_msckf 887, ros2_bag_play 146, latprobe.py 49 |
| SAVIOR-edge (C++) | 3581 | 4 | 4087 | 11.4 / 40 | 25.7 | 10165 / 11304 | 3783 | 2799 | 508 | 142 | 54.5 | run_subscribe_msckf 961, savior_node 452, ros2_bag_play 146, latprobe.py 48 |

## Real-time verdict (pre-registered RT_CRITERION.txt)

| method | R1 every frame masked, 0 fallbacks | R2 keeps up (poses, backlog < 1 s) | R3 mean node_total < 50 ms | R4 latency p99 < 250 ms | R5 RAM < 7 GB, swap growth <= 256 MB | REAL TIME | with margin (node_total p99 < 50 ms) |
|---|---|---|---|---|---|---|---|
| Y-Cls | NO | NO | NO (63.8 ms) | NO (e2e p99 31637.0 ms) | yes (4210 MB, swap +1) | **NO** | no (p99 205.1 ms) |
| SAVIOR (Py) | NO | NO | NO (118.5 ms) | NO (e2e p99 34168.9 ms) | yes (4272 MB, swap +2) | **NO** | no (p99 298.3 ms) |
| SAVIOR (C++) | yes | yes | yes (26.0 ms) | yes (e2e p99 109.7 ms) | yes (2793 MB, swap +0) | **YES** | yes (p99 49.1 ms) |
| SAVIOR-edge (Py) | NO | NO | NO (114.8 ms) | NO (mask_lat p99 36584.7 ms) | yes (4510 MB, swap +1) | **NO** | no (p99 290.6 ms) |
| SAVIOR-edge (C++) | NO | NO | yes (23.8 ms) | yes (mask_lat p99 95.7 ms) | yes (3581 MB, swap +4) | **NO** | no (p99 48.2 ms) |

## TensorRT micro-benchmark (pure GPU time per inference, batch 1, trtbench.py)

| engine | GPU ms median | p90 | min | wall ms median |
|---|--:|--:|--:|--:|
| yolo26s-seg-warehouse.engine | 7.08 | 7.095 | 7.064 | 7.099 |
| yolo26n-seg-warehouse-672.engine | 4.496 | 4.5 | 4.485 | 4.514 |

## Desktop reference (server, RTX PRO 6000 + Threadripper 9960X, rate 1.0; hall_t1_L3 + aisles_t1_L3, results/cpp_port/tables/timing.md, results/edge_study/tables/timing.md)

| run | segment | depth | node_total | OV total |
|---|---|---|---|---|
| py_main_ctrl | 3.8 / 5.8 / 7.7 | 6.2 / 11.9 / 17.2 | 20.0 / 39.2 / 53.2 | 2.9 / 3.9 / 5.5 |
| cpp_main_final | 1.5 / 2.3 / 3.0 | 2.2 / 3.2 / 3.7 | 6.6 / 11.2 / 13.8 | 2.9 / 3.8 / 5.4 |
| e_L250_dfronly | 3.6 / 5.6 / 7.7 | 6.0 / 11.5 / 17.0 | 18.9 / 37.9 / 52.5 | 2.7 / 3.6 / 5.6 |
| openvins | - | - | - | 2.8 / 3.7 / 6.1 |
