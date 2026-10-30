# C++ port timing (Python vs C++ savior_node): median / p90 / p99 / mean ms per frame (savior_node) or per update (ov_msckf)

Idle machine, one container at a time, bag rate 1.0 (20 Hz stereo), 2 start offsets (0.0, 0.6) per method and sequence (hall_t1_L3, aisles_t1_L3). py_main_ctrl = frozen Python savior_node (through the overlay launch), cpp_main_final = C++ savior_node_cpp, cpp_main_composed = C++ node + ov_msckf in one container (intra-process).
savior_node stages: segment = YOLO TensorRT predict + mask transfer; node_total = callback incl. ROS conversion and publish.
ov_* = OpenVINS (ov_msckf record_timing_information): tracking = KLT front-end incl. masking, the rest = back-end.

Hardware: CPU: AMD Ryzen Threadripper 9960X 24-Cores (48 threads, 24 cores, max 5489 MHz); RAM: 125 GiB; GPU: NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition, 97887 MiB, driver 580.178.04, CUDA (driver) 13.0; OS: Linux 7.0.0-38-generic, Docker 29.7.2, image savior:humble-cuda12.8 (sha256:1a13b4aa1cf1)


## Pooled over both sequences

| run | runs | frames | segment | depth | motion | gating | tracking | extension | compose | predict | node_total | ov_tracking | ov_msckf_update | ov_slam_update | ov_retri_marg | ov_total |
|---|--:|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cpp_main_final | 4 | 8844 | 1.5 / 2.2 / 3.0 / 1.6 | 2.1 / 3.1 / 3.9 / 2.1 | 1.6 / 3.1 / 4.1 / 1.8 | 0.4 / 0.9 / 1.3 / 0.4 | 0.1 / 0.5 / 1.1 / 0.2 | 0.0 / 0.0 / 0.0 / 0.0 | 0.4 / 0.6 / 1.0 / 0.4 | - | 6.3 / 10.8 / 13.7 / 6.9 | 1.4 / 1.7 / 2.5 / 1.5 | 0.1 / 0.2 / 0.4 / 0.1 | 0.2 / 0.6 / 1.3 / 0.3 | 1.0 / 1.2 / 1.4 / 1.0 | 3.0 / 3.9 / 5.5 / 3.1 |
| py_main_ctrl | 4 | 8844 | 3.8 / 5.9 / 8.0 / 4.2 | 6.2 / 12.1 / 17.6 / 7.0 | 6.0 / 13.3 / 17.9 / 7.2 | 0.7 / 2.2 / 3.5 / 1.0 | 1.0 / 2.9 / 5.1 / 1.3 | 0.1 / 0.2 / 0.4 / 0.1 | 1.2 / 2.6 / 4.6 / 1.4 | - | 19.8 / 39.4 / 54.2 / 22.9 | 1.5 / 2.0 / 3.6 / 1.6 | 0.1 / 0.2 / 0.5 / 0.1 | 0.2 / 0.6 / 1.4 / 0.3 | 1.0 / 1.3 / 1.7 / 1.0 | 3.1 / 4.2 / 6.3 / 3.3 |

## Per sequence

| run | runs | frames | segment | depth | motion | gating | tracking | extension | compose | predict | node_total | ov_tracking | ov_msckf_update | ov_slam_update | ov_retri_marg | ov_total |
|---|--:|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cpp_main_final@aisles_t1_L3 | 2 | 4340 | 1.7 / 2.4 / 3.1 / 1.8 | 2.4 / 3.4 / 4.1 / 2.3 | 2.2 / 3.5 / 4.5 / 2.2 | 0.5 / 1.1 / 1.4 / 0.6 | 0.2 / 0.6 / 1.2 / 0.3 | 0.0 / 0.0 / 0.0 / 0.0 | 0.4 / 0.7 / 1.1 / 0.4 | - | 7.6 / 11.8 / 14.3 / 7.8 | 1.4 / 1.7 / 2.1 / 1.5 | 0.1 / 0.2 / 0.5 / 0.1 | 0.2 / 0.7 / 1.2 / 0.3 | 1.0 / 1.2 / 1.5 / 0.9 | 3.1 / 4.0 / 5.6 / 3.2 |
| cpp_main_final@hall_t1_L3 | 2 | 4504 | 1.4 / 1.9 / 2.6 / 1.5 | 2.0 / 2.7 / 3.4 / 2.0 | 1.5 / 2.2 / 2.8 / 1.4 | 0.3 / 0.6 / 0.8 / 0.3 | 0.1 / 0.2 / 0.7 / 0.1 | 0.0 / 0.0 / 0.0 / 0.0 | 0.3 / 0.6 / 0.8 / 0.4 | - | 5.8 / 8.3 / 10.4 / 6.0 | 1.4 / 1.7 / 3.7 / 1.5 | 0.1 / 0.2 / 0.4 / 0.1 | 0.1 / 0.5 / 1.4 / 0.2 | 1.0 / 1.2 / 1.4 / 1.0 | 2.9 / 3.7 / 5.4 / 3.0 |
| py_main_ctrl@aisles_t1_L3 | 2 | 4340 | 4.5 / 6.3 / 8.3 / 4.7 | 7.9 / 12.9 / 19.9 / 8.2 | 8.7 / 15.1 / 19.1 / 9.1 | 1.1 / 2.6 / 3.7 / 1.3 | 1.5 / 3.5 / 5.6 / 1.8 | 0.1 / 0.2 / 0.4 / 0.1 | 1.4 / 3.1 / 5.0 / 1.6 | - | 25.8 / 44.2 / 57.0 / 27.4 | 1.5 / 1.9 / 2.5 / 1.6 | 0.1 / 0.2 / 0.5 / 0.1 | 0.2 / 0.7 / 1.2 / 0.3 | 1.0 / 1.2 / 1.5 / 1.0 | 3.2 / 4.2 / 5.9 / 3.4 |
| py_main_ctrl@hall_t1_L3 | 2 | 4504 | 3.4 / 4.8 / 6.8 / 3.7 | 5.6 / 9.5 / 13.2 / 5.9 | 4.9 / 9.0 / 12.8 / 5.5 | 0.5 / 1.4 / 2.5 / 0.7 | 0.6 / 1.8 / 3.5 / 0.9 | 0.1 / 0.1 / 0.3 / 0.1 | 1.1 / 2.2 / 3.6 / 1.3 | - | 16.7 / 29.1 / 41.2 / 18.5 | 1.5 / 2.1 / 3.9 / 1.7 | 0.1 / 0.2 / 0.4 / 0.1 | 0.1 / 0.5 / 1.5 / 0.2 | 1.0 / 1.3 / 1.9 / 1.0 | 3.1 / 4.3 / 6.7 / 3.3 |
