# NIS-gate cross-dataset validation – report (agent aabebf65, saved by the coordinator 2026-10-28)
Frozen methods: sf1_nis, ov_nis (semantic_gate FREEZE 0457d646…). PROTOCOL.yaml md5 865556be… written before any run. Parameter diff exact (185/185).
Validity: t2 and VIODE 240/240; Monado 80/80 (frame rule); OpenLORIS/uHumans2: sf1_nis 102/115 (13 mask-fallback runs, the same offsets as the E SAVIOR baseline), ov_nis 115/115.

| dataset | SAVIOR+NIS vs SAVIOR | vs OV-chi2 x0.25 | vs OpenVINS | OpenVINS+NIS vs OpenVINS |
|---|---|---|---|---|
| Warehouse t2 | −18.7 % [−24, −13] H 6e-8 (seq sf .020) | +8.1 % n.s. (L2+L3 +43 %) | −54.6 % | +31 % (L2+L3 +114 %) |
| VIODE | −15.7 % H 4e-7 | −3.5 % | −37.4 % | −2.1 % n.s. |
| OpenLORIS (8 held-out) | +5.3 % n.s. | – | −1.7 % | −0.5 % |
| uHumans2 (3) | −23.7 % H .09 | – | −16.7 % | −12.8 % |
| Monado, person group | +297 % [+138, +569] H 3e-6 | – | +28 % | +48 % |
| Monado, static MIO07 | +116 % H .006 | – | +109 % | +133 % |

Failures: t2 sf1_nis 4/120 (SAVIOR 4, ov_nis 24); VIODE 6 (SAVIOR 5); Monado person 11/30 (SAVIOR 1, OpenVINS 10).
Learned MSCKF lambda: t2 0.16–0.21, VIODE 0.23–0.26, OpenLORIS 1.0 (the window rarely fills), uHumans2 0.2, Monado person 1.6–2.9, MIO07 6.8.
Reading: on synthetic data the filter is under-confident (lambda < 1), so tightening helps. On real Monado data it learns lambda > 1, opens the gate and degrades, even on the static sequence. The NIS gate is not a safe default.
Caveat: the SG-install flag-off control is 1/5 md5-identical for SAVIOR on hall_t2_L3 (≤ 3 µm); the Monado NIS runs use the SG build.
