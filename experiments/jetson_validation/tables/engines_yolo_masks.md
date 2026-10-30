# On-device TensorRT engines (FP16, built on the Orin NX)

| engine | check | md5 | MB | TensorRT | first predict ms | problems |
|---|---|---|--:|---|--:|---|
| fp16_s | PASS | 22aec943a6e60bcb3a8e7c9c3fcd442d | 25.4 | 10.3.0 | 38.94 | - |
| fp16_n | PASS | a04260d9f3565802ec9f2cfaf52c3321 | 9.3 | 10.3.0 | 35.87 | - |

# Offline YOLO mask agreement (device engine vs desktop engine, every 10th frame, package v1 tolerances)

| engine x seq | verdict | worst class IoU | instance recall | precision | predict ms device (desktop) |
|---|---|--:|--:|--:|---|
| s_hall_t1_L3 | PASS | 0.9908 | 0.9921 | 0.995 | 22.0 (3.9) |
| n_hall_t1_L3 | PASS | 0.9911 | 0.9909 | 0.9927 | 18.3 (5.2) |
| s_aisles_t1_L2 | PASS | 0.9914 | 0.9912 | 0.9934 | 41.3 (7.2) |
| n_aisles_t1_L2 | PASS | 0.9909 | 0.9908 | 0.9919 | 39.4 (6.9) |
