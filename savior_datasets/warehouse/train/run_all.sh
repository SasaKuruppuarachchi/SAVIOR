#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Reproduce the SAVIOR-Warehouse YOLO26-seg fine-tuning, evaluation and export (results/yolo_warehouse/).
# Every python step runs inside savior:humble-cuda12.8 via docker/exec.sh. On a shared host, cap the CPU, e.g.
#   SAVIOR_DOCKER_ARGS="--cpus 10 -e OMP_NUM_THREADS=1 -e MKL_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1" ./run_all.sh
# (without the thread caps every dataloader worker spawns ~4 BLAS/OpenMP threads).
# Steps: ./run_all.sh [data|train|eval|export|bench]...   (default: all, in that order)
set -euo pipefail
WS=${SAVIOR_WS:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXEC="$WS/src/savior/docker/exec.sh"
R=$WS/results/yolo_warehouse
M=$WS/models
MW=$M/warehouse
STEPS=("${@:-data train eval export bench}")
STEPS=(${STEPS[@]})
has() { [[ " ${STEPS[*]} " == *" $1 "* ]]; }
mkdir -p "$R/eval" "$MW"

if has data; then
    "$EXEC" python3 "$HERE/make_yolo_inst.py"                          # instance-consistent YOLO labels
    "$EXEC" python3 "$HERE/make_vio_testset.py" --leak-json "$R/leakage/leakage_check.json"
fi

if has train; then
    # optimiser comparison on yolo26s (paper SGD vs Ultralytics auto = AdamW here), then yolo26n with the winner.
    # As run (results/yolo_warehouse, shared GPU): all three started with epochs=150; s_sgd was stopped after
    # epoch 57 (behind AdamW at every epoch), s_auto was resumed after epoch 96 with the schedule shortened to 110
    # epochs and n_auto after epoch 71 to 95 (train.py --resume <last.pt> --epochs N). The lines below are the
    # closest single-shot equivalent (the LR ramp differs slightly from the resumed runs).
    "$EXEC" python3 "$HERE/train.py" model=$M/yolo26s-seg.pt name=s_sgd optimizer=SGD lr0=0.001 epochs=57
    "$EXEC" python3 "$HERE/train.py" model=$M/yolo26s-seg.pt name=s_auto optimizer=auto epochs=110
    "$EXEC" python3 "$HERE/train.py" model=$M/yolo26n-seg.pt name=n_auto optimizer=auto epochs=95
    cp "$R/runs/s_auto/weights/best.pt" "$MW/yolo26s-seg-warehouse.pt"
    cp "$R/runs/n_auto/weights/best.pt" "$MW/yolo26n-seg-warehouse.pt"
fi

if has eval; then
    for m in yolo26s-seg-warehouse yolo26n-seg-warehouse; do
        "$EXEC" bash -c "cd $R/eval && yolo segment val model=$MW/$m.pt data=$WS/data/warehouse/seg_train/yolo_inst/data.yaml \
            imgsz=672 rect=True batch=16 workers=4 project=$R/eval name=val_$m exist_ok=True plots=True"
        "$EXEC" bash -c "cd $R/eval && yolo segment val model=$MW/$m.pt data=$WS/data/warehouse/seg_test_vio/data.yaml \
            imgsz=672 rect=True batch=16 workers=4 project=$R/eval name=viogray_$m exist_ok=True plots=True"
        for s in vio_gray vio_rgb val val_gray; do
            "$EXEC" python3 "$HERE/eval_seg.py" --model "$MW/$m.pt" --set $s --out "$R/eval/${m}_$s.json"
        done
    done
    for m in yolo26s-seg-warehouse yolo26n-seg-warehouse; do   # sim-to-real proxy on real OpenLORIS frames
        "$EXEC" python3 "$HERE/real_person_check.py" --ft "$MW/$m.pt" --out "$R/eval/real_openloris_person_$m.json"
    done
    for s in vio_gray vio_rgb val val_gray; do          # COCO-pretrained reference on person
        "$EXEC" python3 "$HERE/eval_seg.py" --model "$M/yolo26s-seg.pt" --coco-person --set $s \
            --out "$R/eval/coco_yolo26s_person_$s.json"
    done
fi

if has export; then
    for m in yolo26s-seg-warehouse yolo26n-seg-warehouse; do
        "$EXEC" python3 "$HERE/export.py" --weights "$MW/$m.pt"
        "$EXEC" python3 "$HERE/eval_seg.py" --model "$MW/$m.engine" --set vio_gray --out "$R/eval/${m}_engine_vio_gray.json"
        "$EXEC" bash -c "cd $WS/src/savior/savior_perception && SAVIOR_YOLO_MODEL=$MW/$m.engine \
            PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/test_segmenters.py"
    done
fi

if has bench; then
    "$EXEC" python3 "$HERE/bench_segmenter.py" --out "$R/latency/segmenter.json" --models \
        $MW/yolo26s-seg-warehouse.engine $MW/yolo26n-seg-warehouse.engine $MW/yolo26s-seg-warehouse.pt $M/yolo26s-seg.engine
    for m in yolo26s-seg-warehouse yolo26n-seg-warehouse; do
        "$EXEC" python3 "$HERE/perception_offline_warehouse.py" --dataset warehouse --bag $WS/data/warehouse/ros2/hall_t1_L2 \
            --params $WS/src/savior/savior_bringup/config/warehouse/savior_perception_yolo.yaml \
            --calib $WS/src/savior/savior_bringup/config/warehouse/kalibr_imucam_chain.yaml \
            --roles $WS/src/savior/savior_bringup/config/roles/warehouse.yaml \
            --set segmenter.model=$MW/$m.engine --stats "$R/latency/offline_hall_t1_L2_$m.jsonl" \
            --overlay-dir "$R/latency/overlay_hall_t1_L2_$m" --overlay-every 150
    done
    "$EXEC" python3 "$HERE/offline_stats.py" $R/latency/offline_hall_t1_L2_*.jsonl > $R/latency/offline_stats.txt
    "$EXEC" python3 "$HERE/summarize.py"
fi
