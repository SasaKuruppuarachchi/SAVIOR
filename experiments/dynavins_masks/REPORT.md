# DynaVINS + SAVIOR masks (patch P10) – report (agent a0779435, saved by the coordinator 2026-10-27)

## Build
- P10 = P9 ported to DynaVINS (src/savior/sota/patches/dynavins_savior_mask.patch). Exact-stamp masks, left drop / right gate, no detections on masked pixels, band 128 -> 224 when < 30 features survive, deferred edge mode (smoke-tested only), deterministic + ignore-solver-time keys, plus a new key savior_solver_threads.
- Image savior-sota:noetic-mask-dyna (build_mask_dyna.sh, docker/Dockerfile.savior_mask_dyna). Run scripts: run_one_dm / run_method_dm / drun_sota_dm (the frozen originals are unchanged).

## Determinism
- Only deterministic + ignore-solver-time + 1 solver thread gives md5-identical repeats (4/4). This mode is used for every DynaVINS method, the plain baseline included, and the baseline was re-run in it.
- Cost vs upstream: −0.1 % on t1, t2 and VIODE; failures unchanged.
- Empty-mask control: md5-identical on t1 80/80, t2 120/120 and VIODE 120/120.

## Validation
- 0 missing or bad-size masks; 0 kept features on core pixels; pose-count rule 100 %.
- t1 masks are the same validated folders the VINS+SAVIOR runs used.
- 1224 held-out mask md5s were frozen in a manifest and re-checked before the held-out run.

## t1 (tuning) – paired geometric-mean ATE change vs DynaVINS
| method | L0+L1 | L2+L3 | all |
|---|---|---|---|
| +Y-Cls | −14.4 % n.s. | −4.5 % n.s. | −9.6 % (Holm .04; clu [−25, +5]) |
| +SAVIOR | −24.3 % (Holm .001) | −21.8 % (Holm 6e-5; clu [−34, −6]) | −23.1 % (clu [−39, −7]) |
| +O-Dyn+B | −9.3 % | −3.7 % | −6.5 % |
| +O-Cls+B | +4.6 % | +21.9 % (Holm .001) | +12.9 % |
| SAVIOR vs Y-Cls | −11.6 % | −18.1 % (Holm 2e-6) | −14.9 % (clu [−24, −5]) |

## Held-out t2 (12 sequences, 0 failures for every method)
| vs DynaVINS | L0+L1 | L2+L3 | hall+dock L3 | all |
|---|---|---|---|---|
| +Y-Cls | −2.6 % | −5.0 % | −17.8 % (Holm .01) | −3.8 % |
| +SAVIOR | −2.7 % | −11.2 % [−18, −4] (Holm .02; clu [−26, +7]) | −19.5 % (Holm .01) | −7.1 % (Holm .007; clu [−17, +4]) |
| +O-Dyn+B | −2.4 % | −19.8 % (Holm 1e-5) | −27.4 % | −11.5 % (clu [−20, −3]) |
| +O-Cls+B | +28.8 % | +16.0 % | +23.9 % | +22.3 % |
| SAVIOR vs Y-Cls | −0.1 % | −6.6 % | −2.0 % | −3.4 % (all n.s.) |
| O-Dyn+B vs O-Cls+B | −24 % | −31 % | −41 % | −28 % (clu [−43, −10]) |

- RPE: SAVIOR vs Y-Cls −14.2 % (Holm 6e-17; clu [−21, −9]); Y-Cls +12.6 % vs DynaVINS.
- Sequence-level model (stats_v3, Holm over 7): no SAVIOR effect survives. O-Dyn+B L2+L3 −20 % (p .037, Holm .22).

## Held-out VIODE (failure > 1 m)
- Failures out of 120: DynaVINS 25, +Y-Cls 13, +SAVIOR 12, O-Dyn+B 4, O-Cls+B 4.
- +SAVIOR vs DynaVINS: −40.0 % overall (Holm .006; clu [−67, −3]); −51.8 % at mid+high.
- SAVIOR vs Y-Cls: −1.5 % n.s.
- The gain is almost all parking_lot (late-start divergences): parking_lot −77 %, city_day +3 %, city_night −7 %. With failed pairs excluded: −1.7 % (none+low), −29 % (mid+high).

## Conclusions
1. SAVIOR masks help DynaVINS (t1 −23 %; held-out −7 % on the warehouse, −40 % on VIODE), mostly as robustness.
2. On held-out ATE, SAVIOR ≈ Y-Cls on DynaVINS, so the t1 advantage was optimistic. SAVIOR keeps a −14 % RPE advantage on t2.
3. Dynamic-outlier vs class-level oracle: −28 % on t2 on a third back-end. Perfect class masks hurt DynaVINS.
4. The gain is smaller than on OpenVINS or VINS-Fusion: less headroom, and DynaVINS already down-weights movers.

## Freeze and deviations
- FREEZE.md5 checked before the held-out run.
- One post-held-out, layout-only change to dm_figs.py (frozen copy kept as dm_figs.frozen.py), logged in FREEZE_AMENDMENT.txt.
- Found: the frozen vins_savior run_one.sh fails to write run_info.yaml (3-field COMMITS.txt line), so those runs have no run_info.yaml. Trajectories are unaffected. Fixed only in run_one_dm.sh.
