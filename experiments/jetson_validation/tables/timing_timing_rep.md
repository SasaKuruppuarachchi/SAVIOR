# Jetson Orin NX 8 GB timing (timing_rep): median / p90 / p99 ms, rate 1.0 (20 Hz stereo, real time)

power mode MAXN, jetson_clocks on, GPU [765000000, 765000000, 765000000], other containers: 'none'

Stages per camera frame (savior_node) or per OpenVINS update. classification = motion evidence + interaction gating + tracker (+ band); convert/publish = node_total - convert - segment - pipeline total (ROS conversion, mask publish, callback overhead); OV update = OV total - OV front-end (propagation, MSCKF / SLAM update, marginalisation); mask latency = image -> mask receive, end-to-end = image -> OpenVINS pose receive (latency probe, same machine clock).

| method | runs | segmentation | depth | classification (motion+gating+tracking) | mask compose | convert/publish | savior_node total | OV front-end | OV update | OV total | mask latency | end-to-end latency |
|---|--:|---|---|---|---|---|---|---|---|---|---|---|
| OpenVINS | 4 | - | - | - | - | - | - | 4.1 / 5.1 / 6.2 | 5.0 / 7.6 / 15.4 | 9.3 / 12.0 / 19.5 | - | 14.6 / 18.5 / 68.7 |
| SAVIOR (C++) | 4 | 9.5 / 13.7 / 16.3 | 6.4 / 9.6 / 12.0 | 6.5 / 14.2 / 19.9 | 0.8 / 1.5 / 2.1 | 1.0 / 1.2 / 1.9 | 24.5 / 39.5 / 49.3 | 4.3 / 5.1 / 7.0 | 4.9 / 7.8 / 13.1 | 9.4 / 12.5 / 17.9 | 25.0 / 43.5 / 96.2 | 37.8 / 59.3 / 107.3 |
| SAVIOR-edge (C++) | 4 | 6.8 / 10.7 / 13.1 | 6.3 / 9.8 / 12.3 | 6.6 / 14.8 / 21.0 | 0.8 / 1.6 / 2.3 | 1.0 / 1.2 / 1.8 | 21.8 / 37.2 / 48.0 | 4.4 / 5.7 / 6.8 | 4.6 / 7.6 / 14.5 | 9.4 / 12.4 / 19.1 | 22.2 / 39.7 / 84.1 | 34.3 / 54.2 / 92.3 |

## Per sequence (savior_node total, OV total, end-to-end)

| method | seq | frames | node_total | OV total | mask latency | end-to-end |
|---|---|--:|---|---|---|---|
| OpenVINS | hall_t1_L3 | 4363 | - | 8.6 / 10.8 / 15.1 | - | 13.9 / 16.7 / 67.0 |
| OpenVINS | aisles_t1_L2 | 4197 | - | 10.1 / 13.1 / 21.9 | - | 15.4 / 20.3 / 69.5 |
| SAVIOR (C++) | hall_t1_L3 | 4456 | 23.5 / 30.9 / 38.1 | 8.8 / 11.2 / 15.1 | 23.9 / 31.8 / 84.2 | 35.7 / 44.1 / 85.9 |
| SAVIOR (C++) | aisles_t1_L2 | 4292 | 27.1 / 44.7 / 50.4 | 10.3 / 13.4 / 20.8 | 27.8 / 51.9 / 98.4 | 41.3 / 67.9 / 111.8 |
| SAVIOR-edge (C++) | hall_t1_L3 | 4456 | 20.8 / 27.8 / 34.0 | 8.9 / 11.2 / 15.2 | 21.2 / 28.4 / 73.1 | 33.6 / 39.9 / 63.4 |
| SAVIOR-edge (C++) | aisles_t1_L2 | 4292 | 24.8 / 42.7 / 49.5 | 10.1 / 13.3 / 21.6 | 25.4 / 44.7 / 84.5 | 39.6 / 60.6 / 100.4 |

## Does the filter keep up? (per run)

| method | seq | run | status | images (probe) | savior frames | masks (probe) | OV meas. | exact | fallback latest+empty | late | too_late | n_in_core | hold avg / max ms | poses (OpenVINS-alone) | backlog at end s | mask lat. >50 / >100 / >250 ms |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|---|--:|---|
| OpenVINS | aisles_t1_L2 | run_03 | ok/0 | 2152 | - | - | - | - | - | - | - | 0 | - / - | 2103 (2103) | -0.034 | - |
| OpenVINS | aisles_t1_L2 | run_04 | ok/0 | 2140 | - | - | - | - | - | - | - | 0 | - / - | 2094 (2094) | -0.034 | - |
| OpenVINS | hall_t1_L3 | run_03 | ok/0 | 2234 | - | - | - | - | - | - | - | 0 | - / - | 2186 (2186) | 0.013 | - |
| OpenVINS | hall_t1_L3 | run_04 | ok/0 | 2222 | - | - | - | - | - | - | - | 0 | - / - | 2177 (2177) | 0.014 | - |
| SAVIOR (C++) | aisles_t1_L2 | run_03 | ok/0 | 2150 | 2152 | 2152 | 2152 | 4304 | 0 | 0 | - | 0 | 27.7 / 203.1 | 2103 (2103) | -0.026 | 165 / 9 / 0 |
| SAVIOR (C++) | aisles_t1_L2 | run_04 | ok/0 | 2138 | 2140 | 2138 | 2140 | 4280 | 0 | 0 | - | 0 | 31.5 / 179.1 | 2094 (2094) | -0.025 | 305 / 32 / 0 |
| SAVIOR (C++) | hall_t1_L3 | run_03 | ok/0 | 2232 | 2234 | 2234 | 2234 | 4468 | 0 | 0 | - | 0 | 25.2 / 253.9 | 2185 (2186) | -0.022 | 51 / 15 / 1 |
| SAVIOR (C++) | hall_t1_L3 | run_04 | ok/0 | 2222 | 2222 | 2222 | 2222 | 4444 | 0 | 0 | - | 0 | 25.6 / 253.2 | 2177 (2177) | 0.03 | 73 / 16 / 2 |
| SAVIOR-edge (C++) | aisles_t1_L2 | run_03 | ok/0 | 2152 | 2152 | 2152 | 2152 | 4304 | 0 | 0 | 0 | 0 | 25.1 / 153.7 | 2103 (2103) | -0.004 | 115 / 6 / 0 |
| SAVIOR-edge (C++) | aisles_t1_L2 | run_04 | ok/0 | 2140 | 2140 | 2140 | 2140 | 4280 | 0 | 0 | 0 | 0 | 25.1 / 196.6 | 2094 (2094) | -0.025 | 104 / 6 / 0 |
| SAVIOR-edge (C++) | hall_t1_L3 | run_03 | ok/0 | 2234 | 2234 | 2234 | 2234 | 4468 | 0 | 0 | 0 | 0 | 22.2 / 245.4 | 2186 (2186) | 0.03 | 31 / 15 / 1 |
| SAVIOR-edge (C++) | hall_t1_L3 | run_04 | ok/0 | 2222 | 2222 | 2222 | 2222 | 4444 | 0 | 0 | 0 | 0 | 22.2 / 257.0 | 2177 (2177) | 0.029 | 30 / 16 / 2 |

## Resources (tegrastats 5 Hz over the bag playback, worst / mean over the runs of a method)

Idle baseline (container up, nothing running, 30 s): RAM 2142 MB, VDD_IN 7364 mW, CPU 0.6 %, GR3D 0.0 %.

| method | RAM used max MB (system) | swap growth MB | min MemAvailable MB | GR3D (GPU) mean / p95 % | CPU mean % (6 cores) | VDD_IN mean / p95 mW | VDD_CPU_GPU_CV mean mW | VDD_SOC mean mW | energy / frame mJ (VDD_IN) | above idle mJ / frame | T max C | peak RSS per process MB |
|---|--:|--:|--:|---|--:|---|--:|--:|--:|--:|--:|---|
| OpenVINS | 2414 | 1 | 5202 | 0.0 / 0 | 10.1 | 8131 / 8385 | 2294 | 2584 | 407 | 38 | 52.2 | ros2_bag_play 146, run_subscribe_msckf 90, latprobe.py 47, pose_recorder 44 |
| SAVIOR (C++) | 2818 | 0 | 4794 | 16.6 / 57 | 24.8 | 10897 / 12231 | 4283 | 2906 | 545 | 177 | 54.7 | savior_node 463, ros2_bag_play 145, run_subscribe_msckf 104, latprobe.py 49 |
| SAVIOR-edge (C++) | 2809 | 0 | 4802 | 11.1 / 40 | 24.7 | 10049 / 11247 | 3670 | 2798 | 502 | 134 | 53.9 | savior_node 453, ros2_bag_play 146, run_subscribe_msckf 104, latprobe.py 49 |

## Real-time verdict (pre-registered RT_CRITERION.txt)

| method | R1 every frame masked, 0 fallbacks | R2 keeps up (poses, backlog < 1 s) | R3 mean node_total < 50 ms | R4 latency p99 < 250 ms | R5 RAM < 7 GB, swap growth <= 256 MB | REAL TIME | with margin (node_total p99 < 50 ms) |
|---|---|---|---|---|---|---|---|
| SAVIOR (C++) | yes | yes | yes (26.0 ms) | yes (e2e p99 107.3 ms) | yes (2818 MB, swap +0) | **YES** | yes (p99 49.3 ms) |
| SAVIOR-edge (C++) | yes | yes | yes (23.4 ms) | yes (mask_lat p99 84.1 ms) | yes (2809 MB, swap +0) | **YES** | yes (p99 48.0 ms) |

## Desktop reference (server, RTX PRO 6000 + Threadripper 9960X, rate 1.0; hall_t1_L3 + aisles_t1_L3, results/cpp_port/tables/timing.md, results/edge_study/tables/timing.md)

| run | segment | depth | node_total | OV total |
|---|---|---|---|---|
| py_main_ctrl | 3.8 / 5.8 / 7.7 | 6.2 / 11.9 / 17.2 | 20.0 / 39.2 / 53.2 | 2.9 / 3.9 / 5.5 |
| cpp_main_final | 1.5 / 2.3 / 3.0 | 2.2 / 3.2 / 3.7 | 6.6 / 11.2 / 13.8 | 2.9 / 3.8 / 5.4 |
| e_L250_dfronly | 3.6 / 5.6 / 7.7 | 6.0 / 11.5 / 17.0 | 18.9 / 37.9 / 52.5 | 2.7 / 3.6 / 5.6 |
| openvins | - | - | - | 2.8 / 3.7 / 6.1 |
