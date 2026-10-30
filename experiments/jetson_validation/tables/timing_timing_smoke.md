# Jetson Orin NX 8 GB timing (timing_smoke): median / p90 / p99 ms, rate 1.0 (20 Hz stereo, real time)

power mode MAXN, jetson_clocks on, GPU [765000000, 765000000, 765000000], other containers: 'none'

Stages per camera frame (savior_node) or per OpenVINS update. classification = motion evidence + interaction gating + tracker (+ band); convert/publish = node_total - convert - segment - pipeline total (ROS conversion, mask publish, callback overhead); OV update = OV total - OV front-end (propagation, MSCKF / SLAM update, marginalisation); mask latency = image -> mask receive, end-to-end = image -> OpenVINS pose receive (latency probe, same machine clock).

| method | runs | segmentation | depth | classification (motion+gating+tracking) | mask compose | convert/publish | savior_node total | OV front-end | OV update | OV total | mask latency | end-to-end latency |
|---|--:|---|---|---|---|---|---|---|---|---|---|---|
| SAVIOR (C++) | 1 | 8.8 / 11.1 / 13.6 | 6.4 / 8.4 / 10.9 | 6.1 / 9.5 / 12.6 | 1.0 / 1.6 / 2.2 | 1.0 / 1.1 / 1.6 | 23.7 / 31.6 / 38.4 | 4.2 / 5.0 / 10.1 | 4.4 / 6.3 / 9.4 | 8.8 / 11.2 / 14.8 | 24.0 / 32.6 / 84.5 | 36.1 / 43.8 / 79.8 |

## Per sequence (savior_node total, OV total, end-to-end)

| method | seq | frames | node_total | OV total | mask latency | end-to-end |
|---|---|--:|---|---|---|---|
| SAVIOR (C++) | hall_t1_L3 | 2258 | 23.7 / 31.6 / 38.4 | 8.8 / 11.2 / 14.8 | 24.0 / 32.6 / 84.5 | 36.1 / 43.8 / 79.8 |

## Does the filter keep up? (per run)

| method | seq | run | status | images (probe) | savior frames | masks (probe) | OV meas. | exact | fallback latest+empty | late | too_late | n_in_core | hold avg / max ms | poses (OpenVINS-alone) | backlog at end s | mask lat. >50 / >100 / >250 ms |
|---|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|---|--:|---|
| SAVIOR (C++) | hall_t1_L3 | run_01 | ok/0 | 2258 | 2258 | 2258 | 2258 | 4516 | 0 | 0 | - | 0 | 25.6 / 264.1 | 2185 (-) | -0.016 | 59 / 16 / 3 |

## Resources (tegrastats 5 Hz over the bag playback, worst / mean over the runs of a method)

Idle baseline (container up, nothing running, 30 s): RAM 2062 MB, VDD_IN 7389 mW, CPU 0.9 %, GR3D 0.0 %.

| method | RAM used max MB (system) | swap growth MB | min MemAvailable MB | GR3D (GPU) mean / p95 % | CPU mean % (6 cores) | VDD_IN mean / p95 mW | VDD_CPU_GPU_CV mean mW | VDD_SOC mean mW | energy / frame mJ (VDD_IN) | above idle mJ / frame | T max C | peak RSS per process MB |
|---|--:|--:|--:|---|--:|---|--:|--:|--:|--:|--:|---|
| SAVIOR (C++) | 2732 | 47 | 4904 | 15.3 / 46 | 23.7 | 10745 / 11504 | 4187 | 2883 | 537 | 168 | 54.0 | savior_node 446, ros2_bag_play 145, run_subscribe_msckf 108, latprobe.py 49 |

## Real-time verdict (pre-registered RT_CRITERION.txt)

| method | R1 every frame masked, 0 fallbacks | R2 keeps up (poses, backlog < 1 s) | R3 mean node_total < 50 ms | R4 latency p99 < 250 ms | R5 RAM < 7 GB, swap growth <= 256 MB | REAL TIME | with margin (node_total p99 < 50 ms) |
|---|---|---|---|---|---|---|---|
| SAVIOR (C++) | yes | yes | yes (24.0 ms) | yes (e2e p99 79.8 ms) | yes (2732 MB, swap +47) | **YES** | yes (p99 38.4 ms) |

## Desktop reference (server, RTX PRO 6000 + Threadripper 9960X, rate 1.0; hall_t1_L3 + aisles_t1_L3, results/cpp_port/tables/timing.md, results/edge_study/tables/timing.md)

| run | segment | depth | node_total | OV total |
|---|---|---|---|---|
| py_main_ctrl | 3.8 / 5.8 / 7.7 | 6.2 / 11.9 / 17.2 | 20.0 / 39.2 / 53.2 | 2.9 / 3.9 / 5.5 |
| cpp_main_final | 1.5 / 2.3 / 3.0 | 2.2 / 3.2 / 3.7 | 6.6 / 11.2 / 13.8 | 2.9 / 3.8 / 5.4 |
| e_L250_dfronly | 3.6 / 5.6 / 7.7 | 6.0 / 11.5 / 17.0 | 18.9 / 37.9 / 52.5 | 2.7 / 3.6 / 5.6 |
| openvins | - | - | - | 2.8 / 3.7 / 6.1 |
