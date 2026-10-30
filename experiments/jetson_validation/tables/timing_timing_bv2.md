# Jetson Orin NX 8 GB timing (timing_bv2): median / p90 / p99 ms, rate 1.0 (20 Hz stereo, real time)

power mode MAXN, jetson_clocks on, GPU [765000000, 765000000, 765000000], other containers: 'none'

Stages per camera frame (savior_node) or per OpenVINS update. classification = motion evidence + interaction gating + tracker (+ band); convert/publish = node_total - convert - segment - pipeline total (ROS conversion, mask publish, callback overhead); OV update = OV total - OV front-end (propagation, MSCKF / SLAM update, marginalisation); mask latency = image -> mask receive, end-to-end = image -> OpenVINS pose receive (latency probe, same machine clock).

| method | runs | segmentation | depth | classification (motion+gating+tracking) | mask compose | convert/publish | savior_node total | OV front-end | OV update | OV total | mask latency | end-to-end latency |
|---|--:|---|---|---|---|---|---|---|---|---|---|---|
| OpenVINS | 4 | - | - | - | - | - | - | 4.3 / 6.0 / 8.3 | 5.2 / 9.4 / 20.8 | 10.1 / 14.4 / 25.8 | - | 15.4 / 20.3 / 65.9 |
| SAVIOR (Py) | 4 | 33.8 / 66.1 / 99.1 | 28.5 / 57.2 / 80.9 | 35.6 / 76.8 / 110.7 | 4.5 / 11.4 / 19.3 | 2.5 / 4.2 / 5.5 | 109.1 / 209.6 / 298.7 | 4.6 / 6.2 / 9.3 | 5.6 / 9.9 / 19.6 | 10.7 / 15.2 / 25.6 | 10055.9 / 22654.5 / 37513.3 | 30015.5 / 30025.7 / 30081.1 |
| SAVIOR (C++) | 4 | 9.5 / 13.4 / 15.9 | 6.4 / 9.5 / 11.6 | 6.6 / 14.1 / 20.1 | 0.8 / 1.5 / 2.1 | 1.0 / 1.2 / 2.0 | 24.5 / 38.9 / 48.7 | 4.5 / 5.5 / 10.7 | 5.6 / 9.6 / 17.6 | 10.4 / 14.7 / 23.3 | 24.9 / 41.1 / 115.0 | 38.6 / 57.1 / 120.6 |
| SAVIOR-edge (Py) | 4 | 31.4 / 61.0 / 95.9 | 27.6 / 56.4 / 80.0 | 35.8 / 76.3 / 109.9 | 4.4 / 11.1 / 17.5 | 2.5 / 4.2 / 5.5 | 105.3 / 201.7 / 290.8 | 4.6 / 6.4 / 9.7 | 5.5 / 9.9 / 20.1 | 10.7 / 15.3 / 25.1 | 9509.3 / 21684.1 / 36033.1 | 30015.7 / 30027.9 / 30122.0 |
| SAVIOR-edge (C++) | 4 | 6.8 / 10.6 / 13.0 | 6.3 / 9.7 / 11.7 | 6.6 / 14.7 / 20.9 | 0.8 / 1.6 / 2.3 | 1.0 / 1.2 / 1.7 | 21.8 / 37.0 / 47.4 | 4.8 / 6.4 / 8.7 | 5.2 / 9.2 / 18.0 | 10.6 / 14.5 / 24.3 | 22.3 / 39.6 / 85.6 | 35.7 / 54.8 / 88.9 |

## Per sequence (savior_node total, OV total, end-to-end)

| method | seq | frames | node_total | OV total | mask latency | end-to-end |
|---|---|--:|---|---|---|---|
| OpenVINS | hall_t1_L3 | 2180 | - | 9.3 / 12.1 / 20.0 | - | 14.6 / 17.7 / 64.0 |
| OpenVINS | aisles_t1_L2 | 2098 | - | 11.2 / 16.0 / 27.9 | - | 16.5 / 22.5 / 68.2 |
| SAVIOR (Py) | hall_t1_L3 | 2113 | 91.9 / 179.7 / 241.3 | 10.2 / 14.1 / 22.4 | 8710.4 / 18968.7 / 22143.3 | 30015.3 / 30026.6 / 30091.4 |
| SAVIOR (Py) | aisles_t1_L2 | 1489 | 130.1 / 239.8 / 317.0 | 11.3 / 16.4 / 27.3 | 11766.1 / 32110.6 / 39091.4 | 30015.8 / 30024.6 / 30067.5 |
| SAVIOR (C++) | hall_t1_L3 | 4504 | 23.6 / 31.3 / 37.5 | 9.5 / 13.1 / 20.1 | 24.1 / 32.2 / 78.3 | 37.6 / 45.2 / 68.8 |
| SAVIOR (C++) | aisles_t1_L2 | 4340 | 27.0 / 43.9 / 50.6 | 11.3 / 16.0 / 25.7 | 27.5 / 46.4 / 124.9 | 43.2 / 63.1 / 141.3 |
| SAVIOR-edge (Py) | hall_t1_L3 | 2250 | 87.8 / 166.3 / 200.9 | 10.4 / 14.3 / 21.9 | 8172.1 / 17554.6 / 21415.9 | 30015.5 / 30028.6 / 30178.4 |
| SAVIOR-edge (Py) | aisles_t1_L2 | 1493 | 129.8 / 247.3 / 303.6 | 11.1 / 16.3 / 26.6 | 11530.0 / 31553.7 / 38056.7 | 30016.0 / 30027.2 / 30083.9 |
| SAVIOR-edge (C++) | hall_t1_L3 | 4504 | 20.8 / 28.2 / 33.8 | 10.0 / 12.9 / 19.7 | 21.3 / 28.9 / 67.0 | 34.6 / 41.9 / 55.7 |
| SAVIOR-edge (C++) | aisles_t1_L2 | 4340 | 24.5 / 42.4 / 48.5 | 11.4 / 16.0 / 26.7 | 25.1 / 44.3 / 88.3 | 41.6 / 60.5 / 96.9 |

## Does the filter keep up? (per run)

| method | seq | run | status | images (probe) | savior frames | masks (probe) | OV meas. | exact | fallback latest+empty | late | too_late | n_in_core | hold avg / max ms | poses (OpenVINS-alone) | backlog at end s | mask lat. >50 / >100 / >250 ms |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|---|--:|---|
| OpenVINS | aisles_t1_L2 | run_01 | ok/0 | 2176 | - | - | - | - | - | - | - | 0 | - / - | 1049 (1049) | -0.036 | - |
| OpenVINS | aisles_t1_L2 | run_02 | ok/0 | 2164 | - | - | - | - | - | - | - | 0 | - / - | 1049 (1049) | -0.035 | - |
| OpenVINS | hall_t1_L3 | run_01 | ok/0 | 2256 | - | - | - | - | - | - | - | 0 | - / - | 1090 (1090) | -0.036 | - |
| OpenVINS | hall_t1_L3 | run_02 | ok/0 | 2246 | - | - | - | - | - | - | - | 0 | - / - | 1090 (1090) | -0.036 | - |
| SAVIOR (Py) | aisles_t1_L2 | run_01 | ok/0 | 2176 | 731 | 731 | 822 | 484 | 1160 | 48 | - | 0 | 26347.1 / 30015.9 | 745 (1049) | -0.431 | 731 / 731 / 729 |
| SAVIOR (Py) | aisles_t1_L2 | run_02 | ok/0 | 2164 | 758 | 758 | 816 | 478 | 1154 | 56 | - | 0 | 26382.2 / 30028.3 | 749 (1049) | -0.026 | 758 / 758 / 757 |
| SAVIOR (Py) | hall_t1_L3 | run_01 | ok/0 | 2258 | 1048 | 1048 | 943 | 690 | 1196 | 0 | - | 0 | 26558.7 / 30029.5 | 790 (1090) | -0.037 | 1048 / 1048 / 1047 |
| SAVIOR (Py) | hall_t1_L3 | run_02 | ok/0 | 2246 | 1065 | 1065 | 937 | 690 | 1184 | 0 | - | 0 | 26441.1 / 30029.8 | 790 (1090) | -0.031 | 1065 / 1065 / 1064 |
| SAVIOR (C++) | aisles_t1_L2 | run_01 | ok/0 | 2174 | 2176 | 2174 | 1088 | 2176 | 0 | 0 | - | 0 | 30.6 / 166.8 | 1049 (1049) | -0.014 | 151 / 43 / 0 |
| SAVIOR (C++) | aisles_t1_L2 | run_02 | ok/0 | 2162 | 2164 | 2162 | 1082 | 2164 | 0 | 0 | - | 0 | 30.1 / 155.9 | 1049 (1049) | -0.025 | 127 / 48 / 0 |
| SAVIOR (C++) | hall_t1_L3 | run_01 | ok/0 | 2256 | 2258 | 2258 | 1129 | 2258 | 0 | 0 | - | 0 | 25.6 / 249.7 | 1090 (1090) | -0.022 | 49 / 15 / 0 |
| SAVIOR (C++) | hall_t1_L3 | run_02 | ok/0 | 2244 | 2246 | 2246 | 1123 | 2246 | 0 | 0 | - | 0 | 25.5 / 263.0 | 1090 (1090) | -0.016 | 31 / 15 / 1 |
| SAVIOR-edge (Py) | aisles_t1_L2 | run_01 | ok/0 | 2174 | 763 | 759 | 822 | 502 | 1142 | 44 | 0 | 0 | 26118.0 / 30029.3 | 749 (1049) | -0.035 | 757 / 757 / 755 |
| SAVIOR-edge (Py) | aisles_t1_L2 | run_02 | ok/0 | 2159 | 730 | 724 | 816 | 492 | 1140 | 66 | 0 | 0 | 26158.4 / 30024.4 | 749 (1049) | -0.035 | 721 / 721 / 720 |
| SAVIOR-edge (Py) | hall_t1_L3 | run_01 | ok/0 | 2256 | 1127 | 1127 | 949 | 584 | 1314 | 0 | 0 | 0 | 28331.2 / 30074.1 | 790 (1090) | -0.036 | 1125 / 1125 / 1124 |
| SAVIOR-edge (Py) | hall_t1_L3 | run_02 | ok/0 | 2243 | 1123 | 1121 | 943 | 614 | 1272 | 0 | 0 | 0 | 26740.8 / 30027.2 | 791 (1090) | 0.067 | 1118 / 1118 / 1117 |
| SAVIOR-edge (C++) | aisles_t1_L2 | run_01 | ok/0 | 2176 | 2176 | 2176 | 1088 | 2176 | 0 | 0 | 0 | 0 | 27.4 / 150.9 | 1049 (1049) | -0.026 | 120 / 9 / 0 |
| SAVIOR-edge (C++) | aisles_t1_L2 | run_02 | ok/0 | 2164 | 2164 | 2162 | 1082 | 2164 | 0 | 0 | 0 | 0 | 27.2 / 148.8 | 1049 (1049) | -0.03 | 106 / 6 / 0 |
| SAVIOR-edge (C++) | hall_t1_L3 | run_01 | ok/0 | 2258 | 2258 | 2258 | 1129 | 2258 | 0 | 0 | 0 | 0 | 22.2 / 213.6 | 1090 (1090) | -0.021 | 24 / 13 / 0 |
| SAVIOR-edge (C++) | hall_t1_L3 | run_02 | ok/0 | 2246 | 2246 | 2246 | 1123 | 2246 | 0 | 0 | 0 | 0 | 22.1 / 222.0 | 1090 (1090) | -0.021 | 30 / 13 / 0 |

## Resources (tegrastats 5 Hz over the bag playback, worst / mean over the runs of a method)

Idle baseline (container up, nothing running, 30 s): RAM 2132 MB, VDD_IN 7445 mW, CPU 1.6 %, GR3D 0.0 %.

| method | RAM used max MB (system) | swap growth MB | min MemAvailable MB | GR3D (GPU) mean / p95 % | CPU mean % (6 cores) | VDD_IN mean / p95 mW | VDD_CPU_GPU_CV mean mW | VDD_SOC mean mW | energy / frame mJ (VDD_IN) | above idle mJ / frame | T max C | peak RSS per process MB |
|---|--:|--:|--:|---|--:|---|--:|--:|--:|--:|--:|---|
| OpenVINS | 2394 | 0 | 5276 | 0.0 / 0 | 7.0 | 7850 / 7948 | 2092 | 2545 | 393 | 20 | 51.9 | ros2_bag_play 148, run_subscribe_msckf 89, latprobe.py 47, pose_recorder 44 |
| SAVIOR (Py) | 4009 | 0 | 3642 | 21.1 / 87 | 33.1 | 11171 / 11784 | 4468 | 2918 | 559 | 186 | 54.8 | savior_node 1338, run_subscribe_msckf 549, ros2_bag_play 146, latprobe.py 48 |
| SAVIOR (C++) | 2786 | 1 | 4838 | 16.5 / 54 | 20.8 | 10615 / 11705 | 4078 | 2879 | 531 | 158 | 53.8 | savior_node 464, ros2_bag_play 147, run_subscribe_msckf 103, latprobe.py 48 |
| SAVIOR-edge (Py) | 4173 | 0 | 3469 | 19.1 / 92 | 34.2 | 10906 / 11507 | 4272 | 2884 | 545 | 173 | 54.7 | savior_node 1327, run_subscribe_msckf 545, ros2_bag_play 148, latprobe.py 49 |
| SAVIOR-edge (C++) | 2774 | 0 | 4882 | 11.0 / 40 | 21.2 | 9739 / 10810 | 3446 | 2768 | 487 | 115 | 53.5 | savior_node 452, ros2_bag_play 147, run_subscribe_msckf 103, latprobe.py 48 |

## Real-time verdict (pre-registered RT_CRITERION.txt)

| method | R1 every frame masked, 0 fallbacks | R2 keeps up (poses, backlog < 1 s) | R3 mean node_total < 50 ms | R4 latency p99 < 250 ms | R5 RAM < 7 GB, swap growth <= 256 MB | REAL TIME | with margin (node_total p99 < 50 ms) |
|---|---|---|---|---|---|---|---|
| SAVIOR (Py) | NO | NO | NO (118.7 ms) | NO (e2e p99 30081.1 ms) | yes (4009 MB, swap +0) | **NO** | no (p99 298.7 ms) |
| SAVIOR (C++) | yes | yes | yes (25.9 ms) | yes (e2e p99 120.6 ms) | yes (2786 MB, swap +1) | **YES** | yes (p99 48.7 ms) |
| SAVIOR-edge (Py) | NO | NO | NO (114.7 ms) | NO (mask_lat p99 36033.1 ms) | yes (4173 MB, swap +0) | **NO** | no (p99 290.8 ms) |
| SAVIOR-edge (C++) | yes | yes | yes (23.4 ms) | yes (mask_lat p99 85.6 ms) | yes (2774 MB, swap +0) | **YES** | yes (p99 47.4 ms) |

## Desktop reference (server, RTX PRO 6000 + Threadripper 9960X, rate 1.0; hall_t1_L3 + aisles_t1_L3, results/cpp_port/tables/timing.md, results/edge_study/tables/timing.md)

| run | segment | depth | node_total | OV total |
|---|---|---|---|---|
| py_main_ctrl | 3.8 / 5.8 / 7.7 | 6.2 / 11.9 / 17.2 | 20.0 / 39.2 / 53.2 | 2.9 / 3.9 / 5.5 |
| cpp_main_final | 1.5 / 2.3 / 3.0 | 2.2 / 3.2 / 3.7 | 6.6 / 11.2 / 13.8 | 2.9 / 3.8 / 5.4 |
| e_L250_dfronly | 3.6 / 5.6 / 7.7 | 6.0 / 11.5 / 17.0 | 18.9 / 37.9 / 52.5 | 2.7 / 3.6 / 5.6 |
| openvins | - | - | - | 2.8 / 3.7 / 6.1 |
