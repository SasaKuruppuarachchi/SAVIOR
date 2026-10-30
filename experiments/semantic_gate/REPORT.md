# Semantic chi2 gate (SAVIOR-SG) + NIS control – t1 report (agent a90c78c9, saved by the coordinator 2026-10-27)
Freeze: FREEZE.yaml md5 0457d646d61995b1de656cdd86ecb5bc; GRID.yaml md5 cf463f70… (pre-declared). Install: results/semantic_gate/install (read-only).
Flags-off md5 identity: 96/96 control trajectories byte-identical to the frozen back-end v2 runs. 736/736 runs valid.
Design premise that failed: frozen SAVIOR publishes no 192 band, so m_b and keep_band have no effect.

| method (t1, 80 runs) | vs OpenVINS-v2 | vs SAVIOR | vs SAVIOR, hall L3 | failures > 2 m |
|---|---|---|---|---|
| SAVIOR | −49.4 % | – | – | 0 |
| SG m_s 0.25 (selected) | −49.2 % | +0.4 % n.s. | +9.0 % (Holm .014) | 0 |
| SG m_s 0.5 | −49.2 % | +0.4 % | +4.4 % | 0 |
| SAVIOR + NIS | −59.4 % | −19.8 % (Holm 2e-7) | −26 % | 0 |
| SAVIOR + chi2 x0.25 | −54.9 % | −10.8 % | −17.7 % | 1 |
| OpenVINS + chi2 x0.25 | −46.5 % | +5.6 % | +563 % | 4 |
| OpenVINS + NIS | +23.7 % | – | – | 19 |
| Y-Cls | −26.6 % | – | – | 1 |

- Why SG doesn't help: features on movable objects classified static (26 % of MSCKF tests) are genuinely static and rejected less often than background features.
- The chi2 gain comes from the background: NIS learns lambda ≈ 0.12 (MSCKF) and 0.05 (SLAM, at the clamp), i.e. the filter is under-confident on synthetic data.
- OpenVINS + NIS diverges: dynamic outliers drive lambda up to 20 and open the gate. SAVIOR's masks make the self-tuning gate safe.
- Caveats: selection on t1; the SG pick is a near-tie; the SAVIOR+NIS result depends on the 0.05 floor; the C++ node does not publish the 64 level (NIS needs no new mask level).
