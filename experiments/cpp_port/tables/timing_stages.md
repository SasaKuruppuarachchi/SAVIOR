# Per-stage CPU time per frame: Python vs C++ (desktop, offline, identical frames / detections, 1 OpenCV + BLAS thread)

hall_t1_L3 + aisles_t1_L3, 4434 frames, frame-weighted means [ms]; both pipelines in the same process, interleaved frame by frame (tools/equiv_offline.py --threads 1). C++ "total" = SaviorPipeline::process, Python "total" = SaviorPipeline.process (instance construction excluded in both).

| stage | Python | C++ | C++ / Python |
|---|--:|--:|--:|
| depth | 6.75 | 3.86 | 0.57 |
| motion | 6.91 | 2.32 | 0.34 |
| gating | 0.96 | 0.44 | 0.46 |
| tracking | 1.27 | 0.21 | 0.17 |
| extension | 0.10 | 0.01 | 0.15 |
| compose | 1.39 | 0.40 | 0.29 |
| total | 17.38 | 7.25 | 0.42 |
| m_flow_ego | 1.78 | 0.80 | 0.45 |
| m_assoc | 2.61 | 0.43 | 0.17 |
| m_points | 2.31 | 1.05 | 0.45 |

## Segmenter (same TensorRT engine; wall time per frame incl. pre/post-processing and mask transfer, GPU shared)

| engine | Ultralytics predict (fast_masks) | C++ predict | of which TensorRT enqueue+sync | C++ mask stage |
|---|--:|--:|--:|--:|
| n672 | 3.14 | 1.41 | 0.83 | 0.41 |
| s672 | 3.28 | 1.48 | 0.90 | 0.40 |

## savior_node online (closed loop, quiet machine, rate 1.0; median / p90 / mean ms per frame)

| run | cores | segment | depth | motion | gating | tracking | compose | node_total | ov_total |
|---|---|---|---|---|---|---|---|---|---|
| cpp_main_composed | all 48 | 1.5 / 2.3 / 1.8 | 2.2 / 3.2 / 2.2 | 1.9 / 3.6 / 2.1 | 0.4 / 1.0 / 0.5 | 0.1 / 0.6 / 0.2 | 0.4 / 0.7 / 0.4 | 6.6 / 11.7 / 7.3 | 2.8 / 3.8 / 3.0 |
| cpp_main_final | all 48 | 1.5 / 2.3 / 1.6 | 2.2 / 3.2 / 2.2 | 1.8 / 3.4 / 2.0 | 0.4 / 1.0 / 0.5 | 0.1 / 0.5 / 0.2 | 0.4 / 0.7 / 0.4 | 6.6 / 11.2 / 7.2 | 2.9 / 3.8 / 3.0 |
| py_main_ctrl | all 48 | 3.8 / 5.8 / 4.1 | 6.2 / 11.9 / 7.0 | 6.1 / 13.3 / 7.3 | 0.7 / 2.2 / 1.0 | 1.0 / 2.9 / 1.3 | 1.2 / 2.7 / 1.4 | 20.0 / 39.2 / 22.9 | 2.9 / 3.9 / 3.1 |
| cpp_main_final | 4 (cpuset 0-3) | 1.5 / 2.2 / 1.6 | 2.1 / 3.1 / 2.1 | 1.6 / 3.1 / 1.8 | 0.4 / 0.9 / 0.4 | 0.1 / 0.5 / 0.2 | 0.4 / 0.6 / 0.4 | 6.3 / 10.8 / 6.9 | 3.0 / 3.9 / 3.1 |
| py_main_ctrl | 4 (cpuset 0-3) | 3.8 / 5.9 / 4.2 | 6.2 / 12.1 / 7.0 | 6.0 / 13.3 / 7.2 | 0.7 / 2.2 / 1.0 | 1.0 / 2.9 / 1.3 | 1.2 / 2.6 / 1.4 | 19.8 / 39.4 / 22.9 | 3.1 / 4.2 / 3.3 |
