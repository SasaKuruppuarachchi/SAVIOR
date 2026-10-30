# chi2-realworld: frozen t1-tuned chi2 x0.25 gate on Monado (one-shot, untuned)

Verdict (DECISION_RULE.txt, md5 ad578908...): the tuned-threshold result DOES NOT TRANSFER to real data.
- T1 fails: ovchi_best vs OpenVINS, person group: +292.3 % [+106.9, +646.7] (n = 30).
- T2 fails: ovchi_best vs SAVIOR, person group: ratio 12.18 (+1118 % [+543, +2139]); failures > 1 m 19/30 vs SAVIOR 1/30 (limit 3).
Descriptive: sf1_chibest vs SAVIOR person +218 % [+88, +477] (MIO13 +371, MIO15 +773, MIO16 -22); MIO07 static ovchi_best vs
OpenVINS +38 % [+25, +50], sf1_chibest vs SAVIOR +40 % [+23, +58].
80/80 runs valid at the first attempt (frame rule +-0, chi2 override confirmed in every launch.log); no re-runs.
Full tables: tables/results.md (+ results.json, per_run.csv, param_diff.md). Protocol: PROTOCOL.yaml (md5 e6ac8166...), written before any run.
