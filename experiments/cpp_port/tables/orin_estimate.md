# Orin NX 8 GB per camera frame (20 Hz budget 50 ms): Python vs C++ savior_node (ESTIMATE)

Compute model of results/edge_study (edge_summary.py): desktop CPU per frame = pipeline (offline, 1 thread) + segmenter host side (wall predict - TensorRT enqueue/sync) + node overhead (node_total - pipeline total - segment, online timing); Orin CPU = x 3.5 (range 3.0-4.5); Orin GPU = GFLOPs / 2.7 TFLOPS + 1.5 ms; OpenVINS = desktop ov_total (3.02 ms) x K. Serial sum (no overlap of segmenter GPU time and CPU stages assumed). Not measured on a device.

| segmenter | savior_node | desktop CPU ms (pipeline + seg host + node) | Orin CPU ms [range] | Orin GPU ms | Orin OV ms | Orin total ms [range] | vs Python |
|---|---|--:|--:|--:|--:|--:|--:|
| s672 | python | 20.4 (17.4 + 2.4 + 0.6) | 71 [61-92] | 10.2 | 10.6 | 92 [80-115] | +0 % |
| s672 | cpp | 8.1 (7.2 + 0.6 + 0.3) | 28 [24-36] | 10.2 | 10.6 | 49 [44-60] | -47 % |
| n672 | python | 20.3 (17.4 + 2.3 + 0.6) | 71 [61-91] | 3.9 | 10.6 | 86 [74-109] | +0 % |
| n672 | cpp | 8.1 (7.2 + 0.6 + 0.3) | 28 [24-36] | 3.9 | 10.6 | 43 [37-54] | -50 % |
