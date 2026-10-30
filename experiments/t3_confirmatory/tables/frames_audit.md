# t3 frames audit (AMENDMENT_02 section 1, clarified by AMENDMENT_05) 

clarified rule (used): strict OR tail only = exactly one frame short and it is the last expected stereo pair (the last processed frame is the second-to-last expected one); any other shortfall is invalid and re-run.

valid iff frames processed by the estimator == expected stereo pairs after the start offset (+-0). OpenVINS family: '[TIME] ... seconds total' lines vs bag pairs after the offset passed through the track_frequency drop rule (fed = with a later IMU sample); VINS family: timing.csv frontend rows vs ROS 1 bag pairs after the offset.

roots: ov=/home/sasa/workspace/savior_ws/results/t3_confirmatory/runs vins=/home/sasa/workspace/savior_ws/results/t3_confirmatory/vins_runs dyna=/nonexistent; offsets file /home/sasa/workspace/savior_ws/results/t3_confirmatory/config/t3_offsets.txt

| family | method | runs | strict ok (+-0) | tail only | clarified ok | invalid (clarified) | frames lost (sum) | frames extra (sum) | runs missing | offset source |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| ov | openvins | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | run_info |
| ov | oracle_class_ext | 480 | 471 | 9 | 480 | 0 | 9 | 0 | 0 | run_info |
| ov | oracle_moving_ext | 480 | 479 | 1 | 480 | 0 | 1 | 0 | 0 | run_info |
| ov | ov_nis | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | run_info |
| ov | ovchi_best | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | run_info |
| ov | savior_edge | 480 | 429 | 51 | 480 | 0 | 51 | 0 | 0 | run_info |
| ov | savior_none | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | run_info |
| ov | savior_sg | 480 | 412 | 68 | 480 | 0 | 68 | 0 | 0 | run_info |
| ov | sens_fix1 | 480 | 420 | 60 | 480 | 0 | 60 | 0 | 0 | run_info |
| ov | sf1_chibest | 480 | 436 | 44 | 480 | 0 | 44 | 0 | 0 | run_info |
| ov | sf1_nis | 480 | 428 | 52 | 480 | 0 | 52 | 0 | 0 | run_info |
| ov | yolo_naive | 480 | 456 | 24 | 480 | 0 | 24 | 0 | 0 | run_info |
| vins | dynavins | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | run_info |
| vins | vins_fusion | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_ocls | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_odyn | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_savior | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_ycls | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_zero | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |

**Total: 9120 / 9120 runs pass the clarified frame rule (8811 strict, 309 tail only); 0 invalid.**
