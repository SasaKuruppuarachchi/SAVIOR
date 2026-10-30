# Full-pipeline dynamic masks: Jetson (device FP16 engines, TensorRT 10.3) vs server (desktop FP16 engines, TensorRT 10.16)

Offline Python SaviorPipeline on EVERY stereo frame (lib/pipe_dump.py), same bag + frozen sens_fix1 savior_node keys, only the
engine/platform differs. Per-frame IoU over frames where at least one side has mask pixels; core = 255 (dynamic), band = 192.

Rows "device vs server": Jetson FP16 engine (TensorRT 10.3) vs server FP16 engine (TensorRT 10.16). Rows "FP32 .pt vs server" = the
numerics-only baseline on ONE machine: the same weights run in FP32 PyTorch vs the server FP16 engine (how much a pure
arithmetic difference moves the stateful pipeline).

| comparison | pipeline | seq | frames | identical frames (left core) | pooled IoU left core | per-frame IoU median / p10 / p1 / min | frames IoU >= 0.99 / >= 0.95 | pooled IoU right core | pooled IoU band | same #instances | core px device/server |
|---|---|---|--:|--:|--:|---|---|--:|--:|--:|--:|
| device vs server | SAVIOR | hall_t1_L3 | 2258 | 1.5 % | 0.9886 | 0.9973 / 0.9791 / 0.6607 / 0.309 | 83.6 % / 94.4 % | 0.9891 | - (band off) | 72.5 % | 0.9927 |
| device vs server | SAVIOR | aisles_t1_L2 | 2176 | 13.0 % | 0.9797 | 0.9940 / 0.9430 / 0.2239 / 0.000 | 61.1 % / 88.1 % | 0.9799 | - (band off) | 52.8 % | 1.0029 |
| device vs server | SAVIOR-edge | hall_t1_L3 | 2258 | 1.3 % | 0.9929 | 0.9967 / 0.9834 / 0.9413 / 0.759 | 83.5 % / 98.4 % | 0.9935 | - (band off) | 71.5 % | 0.9985 |
| device vs server | SAVIOR-edge | aisles_t1_L2 | 2176 | 12.5 % | 0.9679 | 0.9927 / 0.8904 / 0.6409 / 0.000 | 55.8 % / 80.0 % | 0.9691 | - (band off) | 45.2 % | 0.9962 |
| FP32 .pt vs server (baseline) | SAVIOR | hall_t1_L3 | 2258 | 1.5 % | 0.9847 | 0.9972 / 0.9802 / 0.4630 / 0.000 | 84.7 % / 92.9 % | 0.9851 | - (band off) | 74.0 % | 0.9957 |
| FP32 .pt vs server (baseline) | SAVIOR | aisles_t1_L2 | 2176 | 13.7 % | 0.9808 | 0.9944 / 0.9494 / 0.2241 / 0.000 | 63.0 % / 89.9 % | 0.9809 | - (band off) | 54.3 % | 1.0027 |
| FP32 .pt vs server (baseline) | SAVIOR-edge | hall_t1_L3 | 2258 | 1.2 % | 0.9886 | 0.9967 / 0.9809 / 0.7846 / 0.495 | 82.1 % / 96.3 % | 0.9893 | - (band off) | 71.6 % | 0.9947 |
| FP32 .pt vs server (baseline) | SAVIOR-edge | aisles_t1_L2 | 2176 | 13.5 % | 0.9751 | 0.9937 / 0.9192 / 0.6484 / 0.000 | 58.9 % / 83.7 % | 0.9761 | - (band off) | 47.2 % | 0.9908 |
