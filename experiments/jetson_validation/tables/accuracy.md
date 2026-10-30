# Closed-loop accuracy on the Jetson vs the desktop (accuracy; rate 0.5, frozen configs, offsets 0.0 / 0.6 / 1.2 s)

overall FAIL (accuracy FAIL, offline masks PASS); sync {'runs': 36, 'valid': 30, 'sync_ok': 30, 'pose_ok': 36, 'mode': 'accuracy'}

| seq | method | verdict | ATE device m (0.0 / 0.6 / 1.2) | ATE desktop m | gm ratio device/desktop | md5 equal | valid | notes |
|---|---|---|---|---|--:|--:|---|---|
| hall_t1_L3 | OpenVINS | PASS | 1001.952 / 4934.484 / 12112.422 | 5.227 / 3393.114 / 5000.542 | - | 0/3 | 3/3 | diverges (> 2.0 m) at every offset on both device and desktop -> PASS |
| hall_t1_L3 | Y-Cls | PASS | 0.218 / 0.218 / 0.271 | 0.243 / 0.495 / 0.200 | 0.812 | 0/3 | 3/3 | gm ratio device/desktop 0.812 over 3 offsets; max device 0.271 m vs desktop 10-offset envelope 0.711 m -> PASS |
| hall_t1_L3 | SAVIOR | FAIL | 0.174 / 0.116 / 1.888 | 0.132 / 0.157 / 0.121 | 2.482 | 0/3 | 3/3 | gm ratio device/desktop 2.482 over 3 offsets; max device 1.888 m vs desktop 10-offset envelope 0.157 m -> FAIL |
| hall_t1_L3 | SAVIOR-edge | PASS | 0.325 / 0.255 / 0.190 | 0.165 / 0.120 / 0.262 | 1.447 | 0/3 | 3/3 | gm ratio device/desktop 1.447 over 3 offsets; max device 0.325 m vs desktop 10-offset envelope 0.411 m -> PASS |
| hall_t1_L3 | SAVIOR (C++) | FAIL | 0.174 / 0.116 / 1.888 | 0.132 / 0.157 / 0.121 | 2.482 | 0/3 | 3/3 | gm ratio device/desktop 2.482 over 3 offsets; max device 1.888 m vs desktop 10-offset envelope 0.157 m -> FAIL |
| hall_t1_L3 | SAVIOR-edge (C++) | PASS | 0.325 / 0.255 / 0.190 | 0.165 / 0.120 / 0.262 | 1.447 | 0/3 | 3/3 | gm ratio device/desktop 1.447 over 3 offsets; max device 0.325 m vs desktop 10-offset envelope 0.411 m -> PASS |
| aisles_t1_L2 | OpenVINS | PASS | 0.075 / 0.182 / 0.208 | 0.246 / 0.229 / 0.135 | 0.718 | 0/3 | 3/3 | gm ratio device/desktop 0.718 over 3 offsets; max device 0.208 m vs desktop 10-offset envelope 0.288 m -> PASS |
| aisles_t1_L2 | Y-Cls | FAIL | 0.077 / 0.077 / 2062.115 | 0.068 / 0.070 / 0.065 | 1.114 | 0/3 | 3/3 | failure class (> 2.0 m) differs at ['run_07'] (desktop fails 0/10 offsets) -> FAIL; gm ratio device/desktop 1.114 over 2 offsets; max device 0.077 m vs desktop 10-offset envelope 0.112 m -> PASS |
| aisles_t1_L2 | SAVIOR | FAIL | 0.095 / 0.111 / 0.134 | 0.154 / 0.138 / 0.103 | 0.862 | 0/3 | 0/3 | gm ratio device/desktop 0.862 over 3 offsets; max device 0.134 m vs desktop 10-offset envelope 0.154 m -> PASS; invalid run(s) (sync / pose count) |
| aisles_t1_L2 | SAVIOR-edge | FAIL | 0.172 / 0.075 / 0.139 | 0.100 / 0.174 / 0.063 | 1.172 | 0/3 | 0/3 | gm ratio device/desktop 1.172 over 3 offsets; max device 0.172 m vs desktop 10-offset envelope 0.197 m -> PASS; invalid run(s) (sync / pose count) |
| aisles_t1_L2 | SAVIOR (C++) | PASS | 0.060 / 0.115 / 0.124 | 0.154 / 0.138 / 0.103 | 0.731 | 0/3 | 3/3 | gm ratio device/desktop 0.731 over 3 offsets; max device 0.124 m vs desktop 10-offset envelope 0.154 m -> PASS |
| aisles_t1_L2 | SAVIOR-edge (C++) | PASS | 0.104 / 0.167 / 0.153 | 0.100 / 0.174 / 0.063 | 1.342 | 0/3 | 3/3 | gm ratio device/desktop 1.342 over 3 offsets; max device 0.167 m vs desktop 10-offset envelope 0.197 m -> PASS |

| seq | ratio | device | desktop (same 3 offsets) | same direction |
|---|---|--:|--:|---|
| hall_t1_L3 | sens_fix1/yolo_naive | 1.435 | 0.469 | False |
| hall_t1_L3 | sens_fix1/openvins | 0.034 | 0.017 | True |
| hall_t1_L3 | savior_edge/sens_fix1 | 0.745 | 1.277 | False |
| aisles_t1_L2 | sens_fix1/yolo_naive | 0.288 | 1.92 | False |
| aisles_t1_L2 | sens_fix1/openvins | 0.793 | 0.661 | True |
| aisles_t1_L2 | savior_edge/sens_fix1 | 1.084 | 0.797 | False |
