# YOLO26-seg fine-tuning on SAVIOR-Warehouse

Date: 2026-10-15. Fine-tuning agent K; report saved by the coordinator.
- Training kit (reproducible): `src/savior/savior_datasets/warehouse/train/`
- Models: `models/warehouse/`
- Results: this directory

## Recommendation
Use **yolo26s-seg-warehouse** (TensorRT FP16, input 672×384). In simulation it beats COCO-pretrained YOLO26s on person. On real images it is much weaker, so on a real robot run a COCO person detector alongside it.

## Data notes
- **Instance labels:** the original YOLO export wrote one instance per polygon, which split occluded objects into several instances (68 % of racks, 55 % of forklifts, 25 % of people). The labels were re-exported with one instance per object to `data/warehouse/seg_train/yolo_inst/` (median IoU with the GT masks 1.00).
- **Grayscale:** the node feeds mono8 images copied to 3 channels, so training used 50 % grayscale augmentation and mono is the main test setting.
- **Splits:** val is hall-layout only. The VIO test set has 444 frames from the 8 sequences (`data/warehouse/seg_test_vio/`).
- **Leakage check passed:** the best match between a test frame and any train/val image is ≤ 0.737 normalised cross-correlation, against ≥ 0.79 for consecutive frames.

## Training
- **Settings:** COCO-pretrained; imgsz 672; batch 16; AMP; seed 0; 150 epochs planned with early-stopping patience 30. Schedules were trimmed because the GPU was shared.
- **Optimiser:** Ultralytics `auto` (AdamW, lr 8.3e-4) beat the paper's SGD at every epoch (val mask mAP50-95 0.231 vs 0.205 at epoch 57).
- **Sim-to-real augmentation:** grayscale, motion and Gaussian blur, down/up-scale, gamma, sensor noise, JPEG.
- **Best val mask mAP50-95:** s 0.252 (epoch 98), n 0.203.

## Results (YOLO26s, VIO-sequence test, mono, confidence 0.25)
Overall mask mAP50-95 is 0.290 (n: 0.238).

| class | AP50-95 | IoU | recall (moving) | precision |
|---|--:|--:|---|--:|
| person | 0.548 | 0.879 | 0.79 (0.91) | 0.88 |
| forklift | 0.330 | 0.791 | 0.65 (0.75) | 0.76 |
| box | 0.427 | 0.858 | 0.70 (0.59) | 0.74 |
| pallet | 0.406 | 0.827 | 0.73 | 0.71 |
| trolley | 0.134 | 0.556 | 0.49 | 0.56 |

- **Size:** objects larger than about 1000 px are almost always found. The misses are small, far objects (forklifts under 1000 px: 5–32 % recall).
- **False positives:** about 1.4 person detections per 100 frames on static structure. 1.6 % of image pixels on static or background regions get covered by a potentially dynamic class.

### Person, fine-tuned vs COCO (YOLO26s)
- **In simulation:** fine-tuned is better on the VIO mono test, AP50-95 0.548 vs 0.449, recall 0.79 vs 0.65, and recall on moving people 0.91 vs 0.76.
- **On real OpenLORIS frames:** the fine-tuned model finds only **37 %** of the COCO model's confident person detections, and 23 % of its own detections have no COCO support. This is a major sim-to-real gap; the training set has only 10 Isaac characters and clean renders.

## Deployment
- **Files:** engines `models/warehouse/yolo26{s,n}-seg-warehouse.engine` (TensorRT 10.16 FP16, static 1×3×384×672) and ONNX opset 17.
- **Accuracy:** FP16 matches the .pt.
- **Tests:** `SAVIOR_YOLO_MODEL=<engine> pytest test_segmenters.py` passes. perception_offline on hall_t1_L2 produced dynamic masks on 1991 of 2258 frames.
- **Latency (desktop, GPU 93–95 % busy with other jobs, so pessimistic):**
  - segment step 39 ms median, of which TensorRT is only 3.4 ms; about 20 ms is Ultralytics post-processing and full-resolution masks for about 58 instances per frame;
  - full node: 51–70 ms median, 86–111 ms p90.

  **This is over the 50 ms frame budget.** Fixes: filter classes before the mask step, or post-process at lower resolution in C++.
- **Jetson Orin NX 8 GB:**
  - build the engine on the device with `yolo export ... format=engine imgsz=384,672 half=True`; a bare `trtexec` engine loses the class names;
  - expect about 1.5–2 GB of the shared memory for the segmenter process.
- **Perception config:** `src/savior/savior_bringup/config/warehouse/savior_perception_yolo.yaml`. Use it with `roles/warehouse.yaml`, and pass `roles_file` explicitly because the launch default is coco_indoor.

## Weaknesses
- **Sim-to-real for person** (above).
- **Trolley** is rare: AP50-95 0.13–0.24.
- **Small objects** are often missed.
- **Rack and window masks** are poor (thin frames), but those classes are static and filtered.
- **Test set:** strong view overlap across the four levels of each trajectory.
- **NMS-free head:** not evaluated.
