# Jetson Orin NX 8 GB on-device validation (2026-10-24/25)

Agent report saved by the coordinator. Setup:
- MAXN with locked clocks (GPU 765 MHz), checked before every session.
- Real-time criterion R1–R5 pre-registered in RT_CRITERION.txt; R2 was amended at 18:50, before any timing run.
- t1 data only.

## Verdict
- **C++ SAVIOR is real time on the device:** 12/12 runs meet R1–R5.
  - Node time 24.5 / 39.5 / 49.1 ms (median / p90 / p99).
  - End-to-end latency 38 / 58 / 110 ms.
- **C++ SAVIOR-edge:** 11/12 runs meet R1–R5. The failing run stalled at start-up: one missing mask combined with the frozen 30 s wait policy.
- **The Python node is not real time:** about 115–119 ms mean per frame.
- **The paper's real-time claim must name the C++ node.**

## Build
- Native build on the device: image `savior:humble-jp6` (base l4t-jetpack r36.4.0, 19.75 GB).
- Two arm64 fixes in src/savior/docker, x86 unchanged:
  - `build.sh`: `--network host` on native arm64 builds;
  - `common.sh`: CDI is used only when a spec of kind nvidia.com/gpu exists.
- Package v2 overlay: scripts/pkg_v2_overlay.

## Engines (FP16, exported on device, 384x672)
| engine | GPU time per inference |
|---|--:|
| warehouse YOLO26s | 7.08 ms |
| YOLO26n | 4.50 ms |

## Accuracy
- **YOLO masks, device vs desktop:** class IoU ≥ 0.991.
- **Dynamic masks, device vs server:** pooled IoU 0.968–0.993, which matches the FP32-vs-FP16 numerics baseline on the server alone.
- **Back-end v2 closed loop:** 18/18 runs valid; device/desktop ATE ratio 0.92–1.32; no failures on the device.
- **Back-end v1 on hall_t1_L3:**
  - SAVIOR (C++): one 1.89 m outlier in 10 offsets;
  - SAVIOR-edge (C++): one failure in 10 offsets.

## Timing (median / p90 / p99 ms)
| pipeline | node total | OpenVINS total | end-to-end |
|---|---|---|---|
| OpenVINS alone | – | 8.9 / 11.6 / 19.0 | 14 / 18 / 78 |
| SAVIOR (C++) | 24.5 / 39.5 / 49.1 | 9.4 / 12.6 / 18.4 | 38 / 58 / 110 |
| SAVIOR-edge (C++) | 22.1 / 37.6 / 48.2 | 9.4 / 12.3 / 18.6 | 40 |
| SAVIOR (Py) | 108.6 / 211 / 298 | | stalls |
| Y-Cls (Py) | 51.8 / 119 / 205 | | stalls |

Per-stage breakdown in tables/timing_timing_*.md.

## Memory and power (VDD_IN rail)
| | RAM peak | node RSS | power | energy per frame |
|---|--:|--:|--:|--:|
| SAVIOR (C++) | 2.8 GB | 0.46 GB | 10.9 W (idle 7.3 W, OpenVINS alone 8.1 W) | 546 mJ |
| Python nodes | 4.2–4.5 GB | | | |

Maximum temperature 56 °C.

## Deployment notes
- The frozen 30 s mask wait is an offline-replay setting. On the device, a single lost mask stalls the filter; deployment needs a 100–250 ms timeout. With a 100 ms timeout, C++ falls back on 0.4–7 % of frames.
- **Left on the Jetson:** image savior:humble-jp6 (19.75 GB) and ~/savior_jetson (7.1 GB).

## Files
- RT_CRITERION.txt
- tables/, figures/, raw/, scripts/
- server/ and verify/ (verify_on_server output for bundle results_agipix1_20261025_0415)
