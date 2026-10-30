# P7 stage F timing: median / p90 / p99 ms per frame (savior_node) or per update (ov_msckf)

Idle machine, one container at a time, bag rate 1.0 (20 Hz stereo), 3 start offsets per method and sequence (hall_t1_L3, aisles_t1_L3). `_fast` / `_slow` = segmenter.fast_masks on / off (bit-identical masks).
savior_node stages: segment = YOLO TensorRT predict + mask transfer; node_total = callback incl. ROS conversion and publish.
ov_* = OpenVINS (ov_msckf record_timing_information): tracking = KLT front-end incl. masking, the rest = back-end.

Hardware: CPU: AMD Ryzen Threadripper 9960X 24-Cores (48 threads, 24 cores, max 5489 MHz); RAM: 125 GiB; GPU: NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition, 97887 MiB, driver 580.178.04, CUDA (driver) 13.0; OS: Linux 7.0.0-38-generic, Docker 29.7.2, image savior:humble-cuda12.8 (sha256:1a13b4aa1cf1)


## Pooled over both sequences

| run | runs | frames | segment | depth | motion | gating | tracking | extension | compose | node_total | ov_tracking | ov_msckf_update | ov_retri_marg | ov_total |
|---|--:|--:|---|---|---|---|---|---|---|---|---|---|---|---|
| openvins | 6 | 12867 | - | - | - | - | - | - | - | - | 1.6 / 1.9 / 2.3 | 0.1 / 0.2 / 0.4 | 0.6 / 0.7 / 1.3 | 2.7 / 3.6 / 5.8 |
| tim_p7_nb_fast | 6 | 13230 | 3.2 / 5.4 / 7.4 | 5.8 / 11.3 / 16.6 | 5.4 / 12.4 / 16.7 | 2.1 / 6.0 / 15.3 | 0.9 / 2.7 / 4.7 | 0.1 / 0.2 / 0.4 | 1.3 / 2.8 / 5.4 | 19.8 / 41.2 / 58.9 | 1.6 / 1.8 / 3.9 | 0.0 / 0.2 / 0.4 | 0.6 / 0.7 / 1.1 | 2.7 / 3.6 / 5.3 |
| tim_p7_nb_slow | 6 | 13230 | 4.2 / 14.4 / 23.9 | 5.8 / 11.5 / 16.7 | 5.5 / 12.7 / 17.1 | 2.1 / 6.0 / 15.3 | 0.9 / 2.8 / 4.9 | 0.1 / 0.2 / 0.4 | 1.3 / 2.8 / 5.4 | 20.9 / 50.6 / 75.6 | 1.6 / 1.8 / 3.9 | 0.0 / 0.2 / 0.4 | 0.6 / 0.7 / 0.8 | 2.7 / 3.6 / 5.3 |
| tim_sens_fix1_fast | 6 | 13230 | 3.2 / 5.3 / 7.4 | 5.8 / 11.3 / 16.5 | 5.5 / 12.4 / 16.6 | 0.7 / 2.1 / 3.4 | 0.9 / 2.7 / 4.7 | 0.1 / 0.2 / 0.3 | 1.2 / 2.5 / 4.4 | 17.9 / 36.5 / 50.5 | 1.6 / 1.8 / 3.9 | 0.0 / 0.2 / 0.4 | 0.6 / 0.7 / 1.0 | 2.7 / 3.6 / 5.3 |
| tim_sens_fix1_slow | 6 | 13230 | 4.2 / 12.9 / 24.2 | 5.9 / 11.4 / 16.8 | 5.5 / 12.6 / 17.4 | 0.7 / 2.1 / 3.5 | 0.9 / 2.7 / 4.9 | 0.1 / 0.2 / 0.3 | 1.2 / 2.5 / 4.5 | 19.0 / 44.6 / 70.8 | 1.6 / 1.8 / 3.8 | 0.0 / 0.2 / 0.4 | 0.6 / 0.7 / 0.8 | 2.7 / 3.7 / 5.4 |
| tim_yolo_naive_fast | 6 | 13230 | 3.3 / 5.4 / 7.3 | 5.8 / 11.3 / 16.3 | - | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 0.1 / 0.4 / 0.6 | 2.2 / 5.7 / 8.4 | 11.8 / 23.3 / 33.8 | 1.6 / 1.9 / 3.8 | 0.0 / 0.1 / 0.3 | 0.6 / 0.7 / 1.2 | 2.6 / 3.4 / 4.8 |
| tim_yolo_naive_slow | 6 | 13230 | 4.2 / 10.9 / 23.3 | 5.8 / 11.4 / 16.5 | - | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 0.1 / 0.4 / 0.6 | 2.2 / 5.8 / 8.7 | 12.6 / 30.0 / 52.6 | 1.6 / 1.9 / 3.9 | 0.0 / 0.1 / 0.3 | 0.6 / 0.7 / 0.8 | 2.6 / 3.4 / 4.9 |

## Per sequence

| run | runs | frames | segment | depth | motion | gating | tracking | extension | compose | node_total | ov_tracking | ov_msckf_update | ov_retri_marg | ov_total |
|---|--:|--:|---|---|---|---|---|---|---|---|---|---|---|---|
| openvins@aisles_t1_L3 | 3 | 6309 | - | - | - | - | - | - | - | - | 1.6 / 2.0 / 2.3 | 0.1 / 0.2 / 0.5 | 0.6 / 0.7 / 1.3 | 2.9 / 3.9 / 6.6 |
| openvins@hall_t1_L3 | 3 | 6558 | - | - | - | - | - | - | - | - | 1.5 / 1.9 / 2.3 | 0.0 / 0.1 / 0.3 | 0.6 / 0.7 / 1.3 | 2.4 / 3.1 / 4.5 |
| tim_p7_nb_fast@aisles_t1_L3 | 3 | 6492 | 3.9 / 5.8 / 7.8 | 7.4 / 12.2 / 18.9 | 8.1 / 14.2 / 18.1 | 2.6 / 9.1 / 17.3 | 1.4 / 3.3 / 5.2 | 0.1 / 0.2 / 0.4 | 1.5 / 3.6 / 5.8 | 25.7 / 49.2 / 62.0 | 1.6 / 1.9 / 2.4 | 0.1 / 0.2 / 0.5 | 0.6 / 0.7 / 1.1 | 2.9 / 3.7 / 5.7 |
| tim_p7_nb_fast@hall_t1_L3 | 3 | 6738 | 2.8 / 4.3 / 5.8 | 5.2 / 8.8 / 12.2 | 4.4 / 8.2 / 11.0 | 1.8 / 4.1 / 7.0 | 0.5 / 1.7 / 3.1 | 0.1 / 0.1 / 0.3 | 1.2 / 2.2 / 3.5 | 16.4 / 29.4 / 40.0 | 1.6 / 1.8 / 4.0 | 0.0 / 0.1 / 0.3 | 0.6 / 0.7 / 1.0 | 2.6 / 3.4 / 5.1 |
| tim_p7_nb_slow@aisles_t1_L3 | 3 | 6492 | 5.6 / 17.2 / 25.6 | 7.5 / 12.3 / 19.1 | 8.1 / 14.6 / 18.4 | 2.6 / 9.1 / 17.4 | 1.4 / 3.4 / 5.3 | 0.1 / 0.2 / 0.4 | 1.6 / 3.7 / 5.8 | 27.6 / 62.6 / 78.9 | 1.6 / 1.9 / 2.4 | 0.1 / 0.2 / 0.5 | 0.6 / 0.7 / 0.8 | 2.8 / 3.7 / 6.0 |
| tim_p7_nb_slow@hall_t1_L3 | 3 | 6738 | 3.3 / 6.5 / 16.3 | 5.2 / 8.8 / 12.3 | 4.5 / 8.3 / 11.3 | 1.8 / 4.2 / 7.2 | 0.6 / 1.7 / 3.2 | 0.1 / 0.1 / 0.3 | 1.2 / 2.3 / 3.6 | 17.0 / 31.6 / 50.8 | 1.6 / 1.8 / 4.0 | 0.0 / 0.1 / 0.3 | 0.6 / 0.7 / 0.8 | 2.6 / 3.5 / 5.0 |
| tim_sens_fix1_fast@aisles_t1_L3 | 3 | 6492 | 3.9 / 5.8 / 7.7 | 7.4 / 12.1 / 18.9 | 8.0 / 14.1 / 18.0 | 1.1 / 2.5 / 3.6 | 1.4 / 3.2 / 5.1 | 0.1 / 0.2 / 0.3 | 1.3 / 2.9 / 4.7 | 23.8 / 41.2 / 53.8 | 1.6 / 1.8 / 2.3 | 0.1 / 0.2 / 0.5 | 0.6 / 0.7 / 0.9 | 2.8 / 3.7 / 5.6 |
| tim_sens_fix1_fast@hall_t1_L3 | 3 | 6738 | 2.9 / 4.2 / 5.7 | 5.2 / 8.8 / 12.3 | 4.4 / 8.1 / 11.1 | 0.5 / 1.3 / 2.4 | 0.5 / 1.7 / 3.1 | 0.1 / 0.1 / 0.2 | 1.1 / 2.1 / 3.4 | 15.1 / 26.3 / 36.6 | 1.6 / 1.8 / 4.0 | 0.0 / 0.1 / 0.3 | 0.6 / 0.6 / 1.1 | 2.6 / 3.5 / 5.2 |
| tim_sens_fix1_slow@aisles_t1_L3 | 3 | 6492 | 5.6 / 16.9 / 25.9 | 7.5 / 12.3 / 19.0 | 8.1 / 14.5 / 18.5 | 1.1 / 2.5 / 3.6 | 1.4 / 3.3 / 5.4 | 0.1 / 0.2 / 0.3 | 1.3 / 3.0 / 4.8 | 26.1 / 53.3 / 75.7 | 1.6 / 1.9 / 2.3 | 0.1 / 0.2 / 0.5 | 0.6 / 0.7 / 0.8 | 2.8 / 3.8 / 5.7 |
| tim_sens_fix1_slow@hall_t1_L3 | 3 | 6738 | 3.3 / 6.4 / 15.9 | 5.2 / 8.9 / 12.3 | 4.5 / 8.2 / 11.1 | 0.5 / 1.3 / 2.4 | 0.5 / 1.7 / 3.1 | 0.1 / 0.1 / 0.2 | 1.1 / 2.1 / 3.4 | 15.6 / 28.9 / 47.3 | 1.6 / 1.8 / 4.0 | 0.0 / 0.1 / 0.3 | 0.6 / 0.7 / 0.8 | 2.6 / 3.5 / 5.2 |
| tim_yolo_naive_fast@aisles_t1_L3 | 3 | 6492 | 4.0 / 5.8 / 7.5 | 7.5 / 12.1 / 18.8 | - | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 0.2 / 0.4 / 0.7 | 3.4 / 6.5 / 8.8 | 15.5 / 25.6 / 36.9 | 1.6 / 1.9 / 2.3 | 0.0 / 0.2 / 0.4 | 0.6 / 0.7 / 1.3 | 2.7 / 3.4 / 4.8 |
| tim_yolo_naive_fast@hall_t1_L3 | 3 | 6738 | 2.9 / 4.3 / 6.0 | 5.2 / 8.8 / 12.3 | - | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 0.1 / 0.3 / 0.4 | 1.5 / 3.9 / 5.7 | 10.0 / 17.7 / 24.1 | 1.6 / 1.8 / 4.0 | 0.0 / 0.1 / 0.3 | 0.6 / 0.7 / 0.8 | 2.6 / 3.4 / 4.9 |
| tim_yolo_naive_slow@aisles_t1_L3 | 3 | 6492 | 5.7 / 16.8 / 25.0 | 7.5 / 12.2 / 19.0 | - | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 0.2 / 0.4 / 0.7 | 3.4 / 6.6 / 9.0 | 17.3 / 37.6 / 57.2 | 1.6 / 1.9 / 2.3 | 0.1 / 0.2 / 0.4 | 0.6 / 0.7 / 1.1 | 2.7 / 3.4 / 4.7 |
| tim_yolo_naive_slow@hall_t1_L3 | 3 | 6738 | 3.2 / 6.4 / 16.3 | 5.2 / 8.8 / 12.2 | - | 0.0 / 0.0 / 0.0 | 0.0 / 0.0 / 0.0 | 0.1 / 0.3 / 0.4 | 1.4 / 3.9 / 5.7 | 10.2 / 19.9 / 34.4 | 1.6 / 1.8 / 4.0 | 0.0 / 0.1 / 0.3 | 0.6 / 0.6 / 0.7 | 2.5 / 3.4 / 4.9 |

## Determinism check
Trajectories (run_01, offset 0.0) are md5-identical between fast_masks on and off, and between the rate-1.0 timing runs and the
rate-0.5 t1 runs, for sens_fix1 and p7_nb on both sequences; OpenVINS alone with record_timing_information on equals P6 openvins
(md5, hall + aisles L3). The timing runs therefore measure exactly the pre-registered pipelines. 42/42 timing runs sync-valid
(tables/sync_check_timing.md). Machine load during the runs: tables/timing_load.txt (load avg <= 2.2, GPU util <= 4 % between runs).
Note: per-stage medians are not additive (node_total median < sum of stage medians); p90/p99 are per-frame tail values.
