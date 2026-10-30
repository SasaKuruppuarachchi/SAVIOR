# C++ port timing (Python vs C++ savior_node): median / p90 / p99 / mean ms per frame (savior_node) or per update (ov_msckf)

Idle machine, one container at a time, bag rate 1.0 (20 Hz stereo), 2 start offsets (0.0, 0.6) per method and sequence (hall_t1_L3, aisles_t1_L3). py_main_ctrl = frozen Python savior_node (through the overlay launch), cpp_main_final = C++ savior_node_cpp, cpp_main_composed = C++ node + ov_msckf in one container (intra-process).
savior_node stages: segment = YOLO TensorRT predict + mask transfer; node_total = callback incl. ROS conversion and publish.
ov_* = OpenVINS (ov_msckf record_timing_information): tracking = KLT front-end incl. masking, the rest = back-end.

Hardware: CPU: AMD Ryzen Threadripper 9960X 24-Cores (48 threads, 24 cores, max 5489 MHz); RAM: 125 GiB; GPU: NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition, 97887 MiB, driver 580.178.04, CUDA (driver) 13.0; OS: Linux 7.0.0-38-generic, Docker 29.7.2, image savior:humble-cuda12.8 (sha256:1a13b4aa1cf1)


## Pooled over both sequences

| run | runs | frames | segment | depth | motion | gating | tracking | extension | compose | predict | node_total | ov_tracking | ov_msckf_update | ov_slam_update | ov_retri_marg | ov_total |
|---|--:|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cpp_main_composed | 4 | 8844 | 1.5 / 2.3 / 7.2 / 1.8 | 2.2 / 3.2 / 3.8 / 2.2 | 1.9 / 3.6 / 4.7 / 2.1 | 0.4 / 1.0 / 1.4 / 0.5 | 0.1 / 0.6 / 1.4 / 0.2 | 0.0 / 0.0 / 0.1 / 0.0 | 0.4 / 0.7 / 1.1 / 0.4 | - | 6.6 / 11.7 / 16.3 / 7.3 | 1.6 / 1.9 / 2.7 / 1.7 | 0.1 / 0.2 / 0.5 / 0.1 | 0.2 / 0.6 / 1.3 / 0.3 | 0.6 / 0.7 / 0.9 / 0.6 | 2.8 / 3.8 / 5.4 / 3.0 |
| cpp_main_final | 4 | 8844 | 1.5 / 2.3 / 3.0 / 1.6 | 2.2 / 3.2 / 3.7 / 2.2 | 1.8 / 3.4 / 4.4 / 2.0 | 0.4 / 1.0 / 1.3 / 0.5 | 0.1 / 0.5 / 1.1 / 0.2 | 0.0 / 0.0 / 0.0 / 0.0 | 0.4 / 0.7 / 1.1 / 0.4 | - | 6.6 / 11.2 / 13.8 / 7.2 | 1.7 / 1.9 / 3.0 / 1.7 | 0.1 / 0.2 / 0.4 / 0.1 | 0.2 / 0.6 / 1.4 / 0.3 | 0.6 / 0.8 / 0.9 / 0.6 | 2.9 / 3.8 / 5.4 / 3.0 |
| py_main_ctrl | 4 | 8844 | 3.8 / 5.8 / 7.7 / 4.1 | 6.2 / 11.9 / 17.2 / 7.0 | 6.1 / 13.3 / 17.8 / 7.3 | 0.7 / 2.2 / 3.5 / 1.0 | 1.0 / 2.9 / 5.0 / 1.3 | 0.1 / 0.2 / 0.4 / 0.1 | 1.2 / 2.7 / 4.6 / 1.4 | - | 20.0 / 39.2 / 53.2 / 22.9 | 1.7 / 1.9 / 2.8 / 1.7 | 0.1 / 0.2 / 0.5 / 0.1 | 0.2 / 0.7 / 1.4 / 0.3 | 0.6 / 0.8 / 1.1 / 0.7 | 2.9 / 3.9 / 5.5 / 3.1 |

## Per sequence

| run | runs | frames | segment | depth | motion | gating | tracking | extension | compose | predict | node_total | ov_tracking | ov_msckf_update | ov_slam_update | ov_retri_marg | ov_total |
|---|--:|--:|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cpp_main_composed@aisles_t1_L3 | 2 | 4340 | 1.7 / 2.5 / 7.8 / 2.0 | 2.5 / 3.4 / 4.0 / 2.4 | 2.6 / 4.0 / 5.1 / 2.6 | 0.5 / 1.1 / 1.4 / 0.6 | 0.3 / 0.8 / 1.5 / 0.4 | 0.0 / 0.0 / 0.1 / 0.0 | 0.4 / 0.8 / 1.1 / 0.4 | - | 8.4 / 12.6 / 18.4 / 8.5 | 1.6 / 1.9 / 2.3 / 1.7 | 0.1 / 0.2 / 0.5 / 0.1 | 0.2 / 0.7 / 1.3 / 0.3 | 0.6 / 0.7 / 0.9 / 0.6 | 3.0 / 3.9 / 5.6 / 3.1 |
| cpp_main_composed@hall_t1_L3 | 2 | 4504 | 1.3 / 1.8 / 7.0 / 1.5 | 2.0 / 2.7 / 3.3 / 2.0 | 1.7 / 2.5 / 3.2 / 1.7 | 0.3 / 0.6 / 0.9 / 0.3 | 0.1 / 0.3 / 1.1 / 0.1 | 0.0 / 0.0 / 0.1 / 0.0 | 0.4 / 0.6 / 0.8 / 0.4 | - | 6.0 / 8.7 / 14.8 / 6.3 | 1.6 / 1.8 / 4.0 / 1.7 | 0.1 / 0.2 / 0.4 / 0.1 | 0.1 / 0.5 / 1.4 / 0.2 | 0.6 / 0.7 / 0.8 / 0.6 | 2.7 / 3.6 / 5.3 / 2.8 |
| cpp_main_final@aisles_t1_L3 | 2 | 4340 | 1.7 / 2.4 / 3.1 / 1.8 | 2.4 / 3.4 / 3.8 / 2.3 | 2.4 / 3.8 / 4.7 / 2.4 | 0.5 / 1.1 / 1.4 / 0.6 | 0.2 / 0.7 / 1.3 / 0.3 | 0.0 / 0.0 / 0.1 / 0.0 | 0.4 / 0.7 / 1.1 / 0.4 | - | 7.9 / 12.2 / 14.1 / 8.1 | 1.7 / 1.9 / 2.3 / 1.7 | 0.1 / 0.2 / 0.5 / 0.1 | 0.3 / 0.7 / 1.2 / 0.3 | 0.6 / 0.8 / 0.9 / 0.6 | 3.0 / 4.0 / 5.6 / 3.1 |
| cpp_main_final@hall_t1_L3 | 2 | 4504 | 1.4 / 1.9 / 2.6 / 1.5 | 2.1 / 2.8 / 3.3 / 2.1 | 1.6 / 2.4 / 3.1 / 1.6 | 0.3 / 0.6 / 0.9 / 0.3 | 0.1 / 0.3 / 0.7 / 0.1 | 0.0 / 0.0 / 0.0 / 0.0 | 0.4 / 0.6 / 0.8 / 0.4 | - | 6.1 / 8.7 / 10.7 / 6.3 | 1.7 / 1.9 / 4.0 / 1.7 | 0.1 / 0.2 / 0.4 / 0.1 | 0.1 / 0.5 / 1.4 / 0.2 | 0.6 / 0.7 / 0.9 / 0.6 | 2.8 / 3.7 / 5.2 / 2.9 |
| py_main_ctrl@aisles_t1_L3 | 2 | 4340 | 4.5 / 6.2 / 8.1 / 4.6 | 8.0 / 12.8 / 19.4 / 8.1 | 8.8 / 15.1 / 18.9 / 9.2 | 1.1 / 2.6 / 3.7 / 1.3 | 1.6 / 3.4 / 5.5 / 1.8 | 0.1 / 0.2 / 0.4 / 0.1 | 1.4 / 3.1 / 4.9 / 1.6 | - | 26.2 / 43.6 / 56.1 / 27.4 | 1.7 / 1.9 / 2.3 / 1.7 | 0.1 / 0.2 / 0.5 / 0.1 | 0.3 / 0.7 / 1.2 / 0.3 | 0.6 / 0.8 / 1.0 / 0.7 | 3.0 / 4.0 / 5.6 / 3.2 |
| py_main_ctrl@hall_t1_L3 | 2 | 4504 | 3.4 / 4.7 / 6.2 / 3.6 | 5.5 / 9.5 / 13.0 / 5.9 | 4.9 / 9.1 / 12.2 / 5.5 | 0.5 / 1.4 / 2.6 / 0.7 | 0.6 / 1.9 / 3.4 / 0.9 | 0.1 / 0.2 / 0.3 / 0.1 | 1.2 / 2.3 / 3.7 / 1.3 | - | 16.7 / 29.1 / 39.6 / 18.5 | 1.7 / 1.9 / 4.1 / 1.7 | 0.1 / 0.2 / 0.4 / 0.1 | 0.1 / 0.6 / 1.5 / 0.2 | 0.6 / 0.8 / 1.1 / 0.7 | 2.8 / 3.8 / 5.5 / 3.0 |
