# M3b Report: controlled SOTA benchmark (VINS-Fusion, DynaVINS, ORB-SLAM3)

Date: 2026-10-24. SOTA benchmark agent; report saved by the coordinator.
- **Protocol (author decision):** the same late-start offsets as our methods; upstream defaults; loop closure off.
- **Volume:** 720 runs, all of which completed the bag.
- **Detailed outputs:** `tables/` (incl. `controlled_*` merged with M2b).

## VIODE (failure > 1 m)
- **Failures out of 120:** OpenVINS 4, VINS-Fusion 16, DynaVINS 25, ORB-SLAM3 34.
- **Pooled ATE vs OpenVINS:**

  | method | ATE change | Holm p |
  |---|---|---|
  | VINS-Fusion | +115 % | H 8e-14 |
  | DynaVINS | +87 % | n.s. |
  | ORB-SLAM3 | +31 % | n.s. |

- **Causes:**
  - the VINS-family failures are deterministic init divergences at specific late-start offsets (DynaVINS is best-in-class from bag start in the validation runs);
  - ORB-SLAM3 fails on city_night from feature starvation.

## Warehouse t2 (held-out, failure > 2 m)
- **Failures out of 120:**

  | method | failures |
  |---|--:|
  | OpenVINS | 19 |
  | VINS-Fusion | **0** |
  | DynaVINS | **0** |
  | ORB-SLAM3 | 120 (never initializes) |
  | Y-Cls | 19 (M2b) |
  | SAVIOR | 10 (M2b) |
  | SAVIOR-edge | 5 (M2b) |
  | O-Dyn+B | 2 (M2b) |

- **Pooled ATE vs OpenVINS:** VINS-Fusion −69 % (L2+L3 −84 %, hall+dock L3 −96 %); DynaVINS −78 % (L2+L3 −88 %, L0 −43 %).
- **Even on static L0, OpenVINS is 1–3× worse than the VINS family:** hall L0 OpenVINS 0.268 m vs VINS-Fusion 0.085 m and DynaVINS 0.106 m.
- **ORB-SLAM3:** the upstream stereo-inertial init needs an inter-frame acceleration change of at least 0.5 m/s², which the smooth simulated motion never provides. This is an init artefact.

## Timing (median per stereo pair, 4 CPUs, quiet)
| method | front-end | back-end | amortised per pair |
|---|---|---|---|
| VINS-Fusion | 5.7–7.3 ms | 11–17 ms per processed frame (every 2nd pair) | 12.8–15.7 ms |
| DynaVINS | 5.5–7.4 ms | 22–53 ms per processed frame (p90 up to 62) | 18–31 ms |
| ORB-SLAM3 | – | – | TrackStereo 14–16 ms + a mapping thread |

For comparison: OpenVINS 2.7 ms; SAVIOR C++ node 7.2 ms.

## Caveats
- **Warehouse configs:** derived from kalibr. VINS IMU noise was scaled from its EuRoC values by the density ratio. DynaVINS's non-calibration parameters come from its VIODE config. Nothing was tuned.
- **ORB-SLAM3 output:** BA-refined (not causal); the VINS outputs are causal.
- **Determinism:** the SOTA methods aren't bit-deterministic.
