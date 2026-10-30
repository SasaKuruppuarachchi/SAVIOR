# t3 frames audit (AMENDMENT_02 section 1, clarified by AMENDMENT_05) _vins

clarified rule (used): strict OR tail only = exactly one frame short and it is the last expected stereo pair (the last processed frame is the second-to-last expected one); any other shortfall is invalid and re-run.

valid iff frames processed by the estimator == expected stereo pairs after the start offset (+-0). OpenVINS family: '[TIME] ... seconds total' lines vs bag pairs after the offset passed through the track_frequency drop rule (fed = with a later IMU sample); VINS family: timing.csv frontend rows vs ROS 1 bag pairs after the offset.

roots: ov=/nonexistent vins=/home/sasa/workspace/savior_ws/results/t3_confirmatory/vins_runs dyna=None; offsets file /home/sasa/workspace/savior_ws/results/t3_confirmatory/config/t3_offsets.txt

| family | method | runs | strict ok (+-0) | tail only | clarified ok | invalid (clarified) | frames lost (sum) | frames extra (sum) | runs missing | offset source |
|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| vins | dynavins | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | run_info |
| vins | vins_fusion | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_ocls | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_odyn | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_savior | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_ycls | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |
| vins | vins_zero | 480 | 480 | 0 | 480 | 0 | 0 | 0 | 0 | offsets_file |

**Total: 3360 / 3360 runs pass the clarified frame rule (3360 strict, 0 tail only); 0 invalid.**
