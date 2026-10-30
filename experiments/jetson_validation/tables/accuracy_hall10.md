# hall_t1_L3, 10 start offsets (0.0-1.8 s), back-end v1, rate 0.5: Jetson C++ node vs desktop (Python = C++ md5-identical there)

| method | device ATE per offset 0.0 ... 1.8 s (m) | desktop ATE per offset (m) | device median [min-max] | desktop median [min-max] | failures > 2 m device / desktop | runs > 0.5 m device / desktop | gm ratio device/desktop (paired, non-failed) |
|---|---|---|---|---|---|---|--:|
| SAVIOR (C++) | 0.174 0.184 0.108 0.116 0.102 0.379 1.888 0.107 0.317 0.104 | 0.132 0.111 0.141 0.157 0.121 0.146 0.121 0.128 0.144 0.110 | 0.145 [0.102-1.888] | 0.130 [0.110-0.157] | 0 / 0 | 1 / 0 | 1.540 |
| SAVIOR-edge (C++) | 0.325 0.332 0.130 0.255 0.135 0.233 0.190 0.207 FAIL(1925) 0.292 | 0.165 0.145 0.130 0.120 0.128 0.184 0.262 0.155 0.187 0.411 | 0.244 [0.130-1924.628] | 0.160 [0.120-0.411] | 1 / 0 | 1 / 0 | 1.274 |
