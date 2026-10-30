# Jetson Orin NX 8 GB timing (timing_deploy): median / p90 / p99 ms, rate 1.0 (20 Hz stereo, real time)

power mode MAXN, jetson_clocks on, GPU [765000000, 765000000, 765000000], other containers: 'none'

Stages per camera frame (savior_node) or per OpenVINS update. classification = motion evidence + interaction gating + tracker (+ band); convert/publish = node_total - convert - segment - pipeline total (ROS conversion, mask publish, callback overhead); OV update = OV total - OV front-end (propagation, MSCKF / SLAM update, marginalisation); mask latency = image -> mask receive, end-to-end = image -> OpenVINS pose receive (latency probe, same machine clock).

| method | runs | segmentation | depth | classification (motion+gating+tracking) | mask compose | convert/publish | savior_node total | OV front-end | OV update | OV total | mask latency | end-to-end latency |
|---|--:|---|---|---|---|---|---|---|---|---|---|---|
| SAVIOR (Py) | 4 | 34.9 / 65.6 / 98.5 | 29.4 / 58.1 / 81.7 | 36.9 / 76.7 / 112.7 | 4.7 / 11.8 / 19.5 | 2.7 / 4.4 / 5.6 | 112.4 / 209.2 / 302.2 | 4.4 / 5.5 / 7.1 | 4.5 / 7.2 / 14.9 | 9.2 / 12.0 / 19.6 | 10421.3 / 23022.0 / 38531.3 | 114.9 / 120.1 / 167.1 |
| SAVIOR (C++) | 4 | 9.5 / 13.8 / 16.5 | 6.4 / 9.5 / 12.0 | 6.5 / 14.0 / 20.1 | 0.8 / 1.5 / 2.1 | 1.0 / 1.2 / 1.8 | 24.4 / 39.3 / 49.7 | 4.3 / 5.0 / 7.1 | 4.9 / 7.7 / 13.8 | 9.3 / 12.5 / 18.5 | 24.8 / 41.9 / 120.3 | 37.9 / 56.7 / 116.1 |
| SAVIOR-edge (Py) | 4 | 32.1 / 61.9 / 97.0 | 27.9 / 56.6 / 80.6 | 36.8 / 77.2 / 111.9 | 4.6 / 11.2 / 17.7 | 2.6 / 4.3 / 5.5 | 107.2 / 204.1 / 296.2 | 4.3 / 5.4 / 7.1 | 4.8 / 7.6 / 15.4 | 9.4 / 12.3 / 20.3 | 9894.8 / 22606.4 / 36361.0 | 115.0 / 120.6 / 167.9 |
| SAVIOR-edge (C++) | 4 | 6.8 / 10.7 / 13.1 | 6.3 / 9.7 / 12.3 | 6.6 / 14.7 / 21.0 | 0.8 / 1.6 / 2.3 | 1.0 / 1.2 / 1.7 | 21.8 / 37.0 / 47.9 | 4.4 / 5.7 / 6.9 | 4.6 / 7.5 / 14.0 | 9.4 / 12.2 / 18.5 | 22.3 / 39.5 / 91.3 | 34.3 / 54.2 / 100.3 |

## Per sequence (savior_node total, OV total, end-to-end)

| method | seq | frames | node_total | OV total | mask latency | end-to-end |
|---|---|--:|---|---|---|---|
| SAVIOR (Py) | hall_t1_L3 | 2292 | 96.1 / 184.9 / 238.9 | 8.6 / 10.2 / 12.3 | 8947.3 / 19219.2 / 22688.8 | 114.1 / 119.3 / 168.3 |
| SAVIOR (Py) | aisles_t1_L2 | 1464 | 132.8 / 239.8 / 321.7 | 10.1 / 13.5 / 21.8 | 12171.5 / 32345.9 / 39157.1 | 115.8 / 121.2 / 165.5 |
| SAVIOR (C++) | hall_t1_L3 | 4504 | 23.6 / 31.1 / 37.6 | 8.7 / 11.3 / 15.2 | 24.0 / 32.0 / 85.2 | 35.9 / 43.4 / 68.7 |
| SAVIOR (C++) | aisles_t1_L2 | 4340 | 26.9 / 44.6 / 51.2 | 10.2 / 13.4 / 20.4 | 27.5 / 55.3 / 137.5 | 41.2 / 72.3 / 119.8 |
| SAVIOR-edge (Py) | hall_t1_L3 | 2199 | 90.2 / 170.2 / 205.9 | 8.9 / 11.1 / 16.7 | 8372.9 / 18190.6 / 22488.3 | 114.5 / 120.3 / 171.6 |
| SAVIOR-edge (Py) | aisles_t1_L2 | 1468 | 130.7 / 249.6 / 307.1 | 10.1 / 13.2 / 21.6 | 12045.8 / 31897.5 / 38418.6 | 115.4 / 120.9 / 162.3 |
| SAVIOR-edge (C++) | hall_t1_L3 | 4504 | 20.9 / 28.3 / 33.7 | 8.9 / 11.0 / 14.3 | 21.3 / 29.0 / 74.9 | 33.5 / 40.1 / 62.9 |
| SAVIOR-edge (C++) | aisles_t1_L2 | 4340 | 24.4 / 42.7 / 49.4 | 10.1 / 13.3 / 20.3 | 25.0 / 44.6 / 93.7 | 39.5 / 60.3 / 107.4 |

## Does the filter keep up? (per run)

| method | seq | run | status | images (probe) | savior frames | masks (probe) | OV meas. | exact | fallback latest+empty | late | too_late | n_in_core | hold avg / max ms | poses (OpenVINS-alone) | backlog at end s | mask lat. >50 / >100 / >250 ms |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|---|--:|---|
| SAVIOR (Py) | aisles_t1_L2 | run_01 | ok/0 | 2174 | 732 | 730 | 2176 | 0 | 4352 | 480 | - | 0 | 101.3 / 115.5 | 2101 (-) | -0.035 | 730 / 730 / 729 |
| SAVIOR (Py) | aisles_t1_L2 | run_02 | ok/0 | 2164 | 732 | 732 | 2164 | 0 | 4328 | 484 | - | 0 | 101.5 / 119.0 | 2101 (-) | -0.034 | 732 / 732 / 730 |
| SAVIOR (Py) | hall_t1_L3 | run_01 | ok/0 | 2254 | 1040 | 1036 | 2258 | 0 | 4516 | 802 | - | 0 | 101.4 / 118.1 | 2184 (-) | 0.012 | 1032 / 1032 / 1031 |
| SAVIOR (Py) | hall_t1_L3 | run_02 | ok/0 | 2246 | 1252 | 1037 | 2246 | 0 | 4492 | 802 | - | 0 | 101.7 / 125.8 | 2184 (-) | 0.012 | 1037 / 1037 / 1036 |
| SAVIOR (C++) | aisles_t1_L2 | run_01 | ok/0 | 2172 | 2176 | 2174 | 2176 | 4275 | 77 | 77 | - | 0 | 29.4 / 127.6 | 2103 (-) | -0.026 | 218 / 38 / 0 |
| SAVIOR (C++) | aisles_t1_L2 | run_02 | ok/0 | 2164 | 2164 | 2160 | 2164 | 4179 | 149 | 149 | - | 0 | 30.7 / 120.4 | 2103 (-) | -0.025 | 255 / 74 / 0 |
| SAVIOR (C++) | hall_t1_L3 | run_01 | ok/0 | 2258 | 2258 | 2258 | 2258 | 4478 | 38 | 38 | - | 0 | 24.9 / 112.4 | 2185 (-) | -0.021 | 49 / 19 / 2 |
| SAVIOR (C++) | hall_t1_L3 | run_02 | ok/0 | 2246 | 2246 | 2246 | 2245 | 4474 | 16 | 16 | - | 0 | 24.3 / 111.1 | 2186 (-) | 0.03 | 43 / 18 / 2 |
| SAVIOR-edge (Py) | aisles_t1_L2 | run_01 | ok/0 | 2176 | 753 | 753 | 2176 | 0 | 4352 | 510 | 0 | 0 | 101.4 / 130.9 | 2101 (-) | -0.035 | 753 / 753 / 751 |
| SAVIOR-edge (Py) | aisles_t1_L2 | run_02 | ok/0 | 2162 | 715 | 713 | 2164 | 0 | 4328 | 294 | 0 | 0 | 101.4 / 124.9 | 2101 (-) | -0.03 | 711 / 711 / 709 |
| SAVIOR-edge (Py) | hall_t1_L3 | run_01 | ok/0 | 2256 | 1092 | 1092 | 2258 | 0 | 4516 | 922 | 0 | 0 | 101.4 / 113.9 | 2184 (-) | 0.013 | 1092 / 1092 / 1091 |
| SAVIOR-edge (Py) | hall_t1_L3 | run_02 | ok/0 | 2238 | 1107 | 1105 | 2246 | 0 | 4492 | 938 | 0 | 0 | 101.4 / 139.7 | 2184 (-) | 0.013 | 1101 / 1101 / 1100 |
| SAVIOR-edge (C++) | aisles_t1_L2 | run_01 | ok/0 | 2173 | 2176 | 2174 | 2176 | 4343 | 9 | 9 | 0 | 0 | 24.9 / 106.2 | 2103 (-) | -0.024 | 103 / 3 / 0 |
| SAVIOR-edge (C++) | aisles_t1_L2 | run_02 | ok/0 | 2164 | 2164 | 2164 | 2164 | 4293 | 35 | 35 | 0 | 0 | 26.5 / 104.6 | 2103 (-) | -0.025 | 166 / 23 / 0 |
| SAVIOR-edge (C++) | hall_t1_L3 | run_01 | ok/0 | 2258 | 2258 | 2258 | 2258 | 4489 | 27 | 27 | 0 | 0 | 22.0 / 110.4 | 2186 (-) | 0.03 | 36 / 15 / 0 |
| SAVIOR-edge (C++) | hall_t1_L3 | run_02 | ok/0 | 2246 | 2246 | 2246 | 2246 | 4464 | 28 | 28 | 0 | 0 | 22.0 / 104.4 | 2186 (-) | 0.029 | 33 / 15 / 1 |

## Resources (tegrastats 5 Hz over the bag playback, worst / mean over the runs of a method)

Idle baseline (container up, nothing running, 30 s): RAM 2159 MB, VDD_IN 7393 mW, CPU 1.0 %, GR3D 0.0 %.

| method | RAM used max MB (system) | swap growth MB | min MemAvailable MB | GR3D (GPU) mean / p95 % | CPU mean % (6 cores) | VDD_IN mean / p95 mW | VDD_CPU_GPU_CV mean mW | VDD_SOC mean mW | energy / frame mJ (VDD_IN) | above idle mJ / frame | T max C | peak RSS per process MB |
|---|--:|--:|--:|---|--:|---|--:|--:|--:|--:|--:|---|
| SAVIOR (Py) | 3745 | 0 | 3871 | 23.7 / 99 | 35.9 | 11300 / 11983 | 4522 | 2951 | 565 | 195 | 64.0 | savior_node 1343, ros2_bag_play 147, run_subscribe_msckf 100, latprobe.py 49 |
| SAVIOR (C++) | 2826 | 0 | 4792 | 16.6 / 54 | 24.0 | 10926 / 12261 | 4303 | 2910 | 546 | 177 | 54.9 | savior_node 462, ros2_bag_play 149, run_subscribe_msckf 112, latprobe.py 49 |
| SAVIOR-edge (Py) | 3947 | 0 | 3679 | 21.1 / 99 | 35.6 | 11016 / 11546 | 4313 | 2912 | 551 | 181 | 54.9 | savior_node 1349, ros2_bag_play 148, run_subscribe_msckf 120, latprobe.py 49 |
| SAVIOR-edge (C++) | 2819 | 2 | 4823 | 11.4 / 40 | 24.9 | 10039 / 11168 | 3662 | 2798 | 502 | 132 | 54.1 | savior_node 452, ros2_bag_play 147, run_subscribe_msckf 104, latprobe.py 49 |

## Real-time verdict (pre-registered RT_CRITERION.txt)

| method | R1 every frame masked, 0 fallbacks | R2 keeps up (poses, backlog < 1 s) | R3 mean node_total < 50 ms | R4 latency p99 < 250 ms | R5 RAM < 7 GB, swap growth <= 256 MB | REAL TIME | with margin (node_total p99 < 50 ms) |
|---|---|---|---|---|---|---|---|
| SAVIOR (Py) | NO | yes | NO (121.2 ms) | yes (e2e p99 167.1 ms) | yes (3745 MB, swap +0) | **NO** | no (p99 302.2 ms) |
| SAVIOR (C++) | NO | yes | yes (26.0 ms) | yes (e2e p99 116.1 ms) | yes (2826 MB, swap +0) | **NO** | no (p99 49.7 ms) |
| SAVIOR-edge (Py) | NO | yes | NO (117.0 ms) | NO (mask_lat p99 36361.0 ms) | yes (3947 MB, swap +0) | **NO** | no (p99 296.2 ms) |
| SAVIOR-edge (C++) | NO | yes | yes (23.4 ms) | yes (mask_lat p99 91.3 ms) | yes (2819 MB, swap +2) | **NO** | no (p99 47.9 ms) |

## Desktop reference (server, RTX PRO 6000 + Threadripper 9960X, rate 1.0; hall_t1_L3 + aisles_t1_L3, results/cpp_port/tables/timing.md, results/edge_study/tables/timing.md)

| run | segment | depth | node_total | OV total |
|---|---|---|---|---|
| py_main_ctrl | 3.8 / 5.8 / 7.7 | 6.2 / 11.9 / 17.2 | 20.0 / 39.2 / 53.2 | 2.9 / 3.9 / 5.5 |
| cpp_main_final | 1.5 / 2.3 / 3.0 | 2.2 / 3.2 / 3.7 | 6.6 / 11.2 / 13.8 | 2.9 / 3.8 / 5.4 |
| e_L250_dfronly | 3.6 / 5.6 / 7.7 | 6.0 / 11.5 / 17.0 | 18.9 / 37.9 / 52.5 | 2.7 / 3.6 / 5.6 |
| openvins | - | - | - | 2.8 / 3.7 / 6.1 |
