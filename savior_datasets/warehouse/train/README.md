# YOLO26-seg fine-tuning for SAVIOR-Warehouse

This directory fine-tunes COCO-pretrained YOLO26n-seg and YOLO26s-seg on the SAVIOR-Warehouse segmentation set. The
set is synthetic (Isaac Sim 6.0), with 8 classes, and the models are trained **only in simulation**. The scripts
evaluate the models on the segmentation val split and on frames from the VIO sequences, and export TensorRT FP16 and
ONNX (opset 17) models for `savior_perception`. Everything runs in `savior:humble-cuda12.8` via `docker/exec.sh`.
`run_all.sh` reproduces the whole chain: `./run_all.sh [data|train|eval|export|bench]`.

Outputs:
* weights and engines: `models/warehouse/`;
* runs, metrics, plots and tables: `results/yolo_warehouse/`;
* node config: `savior_bringup/config/warehouse/savior_perception_yolo.yaml`.

## Files

| file | purpose |
|---|---|
| `make_yolo_inst.py` | Builds instance-consistent YOLO labels in `data/warehouse/seg_train/yolo_inst/` (see below) |
| `make_vio_testset.py` | Builds the VIO-sequence test set `data/warehouse/seg_test_vio/` (RGB + mono variants) and runs the frame-leakage check |
| `simreal_aug.py` | Sim-to-real photometric augmentation; it replaces Ultralytics' Albumentations stage |
| `train_cfg.yaml`, `train.py` | Hyperparameters and the training wrapper (`--resume last.pt --epochs N` re-installs the aug) |
| `eval_seg.py` | Evaluation at mask level, as the node uses the model: AP, semantic IoU, recall vs area, moving/static, false positives on static structure, pixel confusion |
| `real_person_check.py` | Real-image person proxy on OpenLORIS (COCO-pretrained detections as pseudo-GT) |
| `export.py` | TensorRT FP16 engine and ONNX opset 17, both static 384x672 |
| `bench_segmenter.py`, `offline_stats.py`, `perception_offline_warehouse.py` | Segment latency; node pipeline latency via `savior_bringup/tools/perception_offline.py` (the wrapper adds `--dataset warehouse` without editing the tool) |
| `summarize.py` | `training_curves.png` and `tables/*.csv` |

## Data decisions

* **Instance-consistent labels.** `tools/coco_to_yolo.py` writes one YOLO line per *polygon*. As a result, an
  instance that occlusion splits into parts becomes several instances. This affects 68 % of the rack, 55 % of the
  forklift and 25 % of the person instances in train. `make_yolo_inst.py` keeps one line per COCO instance and bridges
  the parts with `ultralytics.data.converter.merge_multi_segment`, the scheme Ultralytics uses for COCO-seg. When the
  bridged polygons are rasterised the way Ultralytics does it, they match the uint16 GT masks with a median IoU of
  1.00 (mean 0.945; RETR_EXTERNAL fills holes).
* **Val is hall-only.** The val seeds (1007 and 1015) are odd, so they all use the hall base layout. The VIO test set
  covers both scenes.
* **VIO test set.** It takes every 40th frame of all 8 sequences, with level Lk offset by 10·k frames: 444 frames and
  38.8 k instances (915 person, 693 forklift, 23.2 k box, 144 trolley). The GT is the exact `seg0` instance masks,
  with classes from `instances.json` and moving flags from `moving.csv`. `test_gray` is BT.601 luma replicated to 3
  channels, which is exactly what `savior_node` feeds YOLO from the mono8 `/cam0/image_raw`. **This is the primary
  test.**
* **Leakage check.** 96x54 NCC thumbnails were compared against all 2720 train and val images. The best match per
  test frame is at most 0.737 (mean 0.50). For comparison, the same pose across L0/L1 gives ≥ 0.95 (p05), and
  consecutive frames give ≥ 0.79 (p05). The closest pairs show the same building but different views
  (`results/yolo_warehouse/leakage/`). The same static scene appears in both sets; the same frames do not.

## Training recipe (YOLO26s / YOLO26n, Ultralytics 8.4.177)

* **Input and schedule.**
  * Weights: COCO-pretrained, with `cls_remap` (the person head row is initialised from COCO 'person').
  * Input: imgsz 672, square mosaic training; batch 16 (nbs 64), AMP, seed 0, deterministic.
  * Workers: 8 dataloader workers, with BLAS/OMP threads set to 1 and `--cpus 10` on the shared host.
  * Schedule: 150 epochs, patience 30, close_mosaic 10.
* **Optimiser.** `optimizer=auto` resolves to **AdamW, lr0 = 8.33e-4, β1 0.9, wd 5e-4, warm-up 3 epochs, linear
  decay to 0.01·lr0**. MuSGD is chosen only above 10 k iterations, and here there are 38 × 150. The alternative is
  the paper's **SGD (lr0 1e-3, momentum 0.9, wd 5e-4, nesterov)**; Ultralytics has no step decay, so it uses linear
  decay. On YOLO26s, AdamW led at every epoch:
  * val mask mAP50-95 at epoch 10 / 30 / 57: 0.193 / 0.221 / 0.231 for AdamW, against 0.162 / 0.188 / 0.205 for SGD;
  * SGD reached at epoch 57 what AdamW reached at about epoch 15.

  SGD was therefore stopped after epoch 57, and AdamW was selected by validation. With lr 1e-3 for a YOLO
  fine-tune, the paper's YolactEdge setting under-trains within this budget.
* **Augmentation.**
  * Geometric and photometric: HSV (h 0.015, s 0.7, v 0.4), mosaic 1.0, scale ±0.5, translate 0.1, fliplr 0.5,
    copy-paste 0.1 (flip mode).
  * `simreal_aug.py`, sampled independently per image:
    * gray 0.5;
    * motion blur 0.2 (3–9 px, any angle; about 7 px at 89°/s and 10 ms exposure);
    * Gaussian blur 0.15 (σ 0.3–1.2);
    * down/up-scale 0.1 (0.5–0.8);
    * gamma/contrast 0.25;
    * sensor noise 0.4 (σ 2–8 DN plus a shot term, 50 % luma-correlated);
    * JPEG 0.2 (q 40–90).
  * `results/yolo_warehouse/simreal_aug_examples.jpg` shows samples.
* **Interrupted runs.** The GPU was shared with about 20 foreign training jobs, and epochs slowed from 55 s to
  270 s. YOLO26s was therefore resumed after epoch 96 with the schedule shortened to 110 epochs; its best epoch was
  98. YOLO26n was resumed after epoch 71 with 95 epochs; its best epoch was 82. `run_all.sh` lists the single-shot
  equivalents.

## Results (details: `results/yolo_warehouse/`)

Val split, Ultralytics `val`, mask mAP50 / mAP50-95 (box mAP50-95 in brackets):

| class | YOLO26s | YOLO26n |
|---|---|---|
| all | 0.532 / 0.252 (0.528) | 0.446 / 0.202 (0.414) |
| person | 0.745 / 0.425 | 0.686 / 0.382 |
| forklift | 0.747 / 0.418 | 0.664 / 0.350 |
| box | 0.579 / 0.266 | 0.502 / 0.228 |
| pallet | 0.556 / 0.257 | 0.432 / 0.187 |
| trolley | 0.636 / 0.240 | 0.488 / 0.158 |
| rack | 0.302 / 0.099 | 0.224 / 0.069 |
| guard_rail | 0.589 / 0.286 | 0.478 / 0.223 |
| window | 0.099 / 0.024 (box 0.667) | 0.098 / 0.023 |

The VIO test set (mono) and the person comparison with COCO-pretrained YOLO26s are in
`results/yolo_warehouse/tables/`. On the mono VIO test, YOLO26s gets person AP50-95 0.548 against 0.449 for COCO,
and recall 0.79 against 0.65. On real OpenLORIS frames, however, it recovers only 37 % of the people the COCO model
finds with confidence ≥ 0.5. Read the caveats below before deploying on real data.

## Caveats

* **Sim-to-real.** The training set has only 10 Isaac characters, and the renders are clean.
  * On real images (OpenLORIS T265 mono), the fine-tuned models lose most of their person recall relative to COCO.
  * For real-world use, run COCO-person alongside the warehouse model, or re-validate on real data. Mixing real
    person images into training would end the "trained only in simulation" claim.
* **Classes.**
  * Trolley is rare (813 train / 144 test instances): mask AP50-95 is 0.13–0.24, and recall of small trolleys is
    ≤ 0.2.
  * Window and rack masks are poor, because the GT polygons are thin frames with filled holes. These classes are
    static and are filtered out by `filter_classes`.
* **Engines.**
  * Engines use the default Ultralytics export (one-to-many head + NMS), the same path the validation used.
  * A trtexec-built plan has no Ultralytics metadata (class names), so build the Jetson engine with `yolo export`
    (see `export.py`).
