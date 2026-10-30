# P3a feature fates (diagnostic OpenVINS build = install + logging only; trajectories equal to <= 4e-6 m)

human track = >= 50 % of its observations on the oracle human mask (cam0 GT seg, cam1 stereo-warped); post-init tracks only.

| run | kept obs on human cam0 / cam1 | frames with >= 1 human feature | human tracks / all | median (mean) length human vs other [frames] | human: used / chi2 / trifail / few / SLAM | MSCKF chi2 reject rate human vs other | share of MSCKF-used measurements on humans | share of SLAM-update meas. on humans |
|---|--:|--:|--:|--:|---|--:|--:|--:|
| 06h_observe_run01 | 0.56 % / 0.56 % | 20.5 % | 384 / 20876 | 3 (8.8) vs 10 (30.8) | 9 / 29 / 41 / 20 / 1 % | 77 % vs 36 % | 0.28 % | 0.020 % |
| 06h_observe_run03 | 0.60 % / 0.79 % | 21.6 % | 378 / 20620 | 3 (10.7) vs 10 (31.1) | 12 / 28 / 36 / 20 / 1 % | 69 % vs 34 % | 0.42 % | 0.013 % |
| 12h_observe_run01 | 1.18 % / 0.98 % | 39.9 % | 726 / 22414 | 3 (9.4) vs 11 (32.6) | 9 / 26 / 42 / 20 / 1 % | 74 % vs 37 % | 0.76 % | 0.109 % |
| 12h_observe_run01_dil4 | 2.36 % / 1.96 % | 53.4 % | 1267 / 22414 | 3 (11.1) vs 11 (33.1) | 8 / 25 / 43 / 21 / 1 % | 76 % vs 36 % | 1.35 % | 0.249 % |
| 12h_observe_run03 | 1.10 % / 0.97 % | 35.3 % | 656 / 22401 | 3 (8.2) vs 11 (32.6) | 8 / 29 / 36 / 23 / 1 % | 78 % vs 39 % | 0.46 % | 0.058 % |
| 12h_openvins_run01 | 1.21 % / 1.04 % | 39.9 % | 701 / 22354 | 3 (9.8) vs 11 (32.6) | 11 / 27 / 40 / 20 / 0 % | 72 % vs 38 % | 0.79 % | 0.093 % |
| 12h_oracle_person_run01 | 0.04 % / 0.02 % | 2.4 % | 60 / 21518 | 2 (2.6) vs 11 (33.0) | 13 / 8 / 45 / 33 / 0 % | 38 % vs 38 % | 0.06 % | 0.000 % |
