# Closed loop with the re-frozen OpenVINS back-end v2 (results/backend_v2/backend_config.yaml md5 10c2144b: track_frequency 10.5, max_clones 15)

Jetson (C++ node for SAVIOR / SAVIOR-edge, rate 0.5, offsets 0.0 / 0.6 / 1.2 s) vs the desktop back-end v2 runs of the same pipeline
(Python node, results/backend_v2/runs, same offsets = run_01 / 04 / 07). Failure = ATE > 2 m.

| seq | method | ATE device m (0.0 / 0.6 / 1.2) | ATE desktop m | gm ratio (both < 2 m) | failures device / desktop (3) | desktop 10-offset range (non-failed) |
|---|---|---|---|--:|---|---|
| hall_t1_L3 | OpenVINS | 1.261 / FAIL (11445) / FAIL (5618) | 1.250 / FAIL (11097) / FAIL (6309) | 1.009 | 2 / 2 | 1.250-1.492 (2/10) |
| hall_t1_L3 | SAVIOR (C++) | 0.127 / 0.130 / 0.115 | 0.101 / 0.110 / 0.073 | 1.322 | 0 / 0 | 0.073-0.113 (10/10) |
| hall_t1_L3 | SAVIOR-edge (C++) | 0.106 / 0.110 / 0.185 | 0.094 / 0.119 / 0.097 | 1.259 | 0 / 0 | 0.090-0.178 (10/10) |
| aisles_t1_L2 | OpenVINS | 0.075 / 0.137 / 0.127 | 0.051 / 0.136 / 0.096 | 1.246 | 0 / 0 | 0.051-0.143 (10/10) |
| aisles_t1_L2 | SAVIOR (C++) | 0.063 / 0.076 / 0.076 | 0.073 / 0.079 / 0.081 | 0.920 | 0 / 0 | 0.055-0.107 (10/10) |
| aisles_t1_L2 | SAVIOR-edge (C++) | 0.057 / 0.078 / 0.068 | FAIL (1260) / 0.082 / 0.068 | 0.978 | 0 / 1 | 0.064-0.104 (9/10) |
