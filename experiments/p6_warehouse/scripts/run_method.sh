#!/usr/bin/env bash
# run_method.sh <seq> <method> <domain>   -> results/p6_warehouse/<seq>/<method>/run_XX (one container, offsets in series)
# env: OFFSETS (default 10 offsets "0.0 0.2 ... 1.8", all inside the 3 s hover), START (run index of the first offset,
#      default 1), RATE (default 0.5), DIAG=1: diagnostic OpenVINS overlay (feature-fate log run_XX/diag_updates.csv)
# Bags: data/warehouse/ros2_stereoseg/<seq> = data/warehouse/ros2/<seq> + /cam1/segmentation(_moving) (GT right masks).
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentL
B=$WS/src/savior/savior_bringup/config
CFG=$B/warehouse/estimator_config.yaml
BAG=$WS/data/warehouse/ros2_stereoseg/$SEQ
RATE=${RATE:-0.5}
MODEL_WH=$WS/models/warehouse/yolo26s-seg-warehouse.engine
MODEL_COCO=$WS/models/yolo26s-seg.engine
PP_YOLO=$B/warehouse/savior_perception_yolo.yaml
LAUNCH=savior.launch.py
OVSET="deterministic_processing=true dynamic_mask_upstream_compat=true"
PSET=""
ARGS=()
TOPICS="/cam0/image_raw /cam1/image_raw /imu0 /tf_static"
P4="motion.enable=true gating.link_depth=contact gating.max_noise_m=0.5 tracker.enable=false extension.enable=true motion.still_policy=unmask compose.right_fallback=median"
P2="motion.enable=false gating.link_depth=contact gating.max_noise_m=0.5 tracker.enable=false extension.enable=true compose.right_fallback=median"
ORACLE="extension.enable=false tracker.enable=false"
YOLO_WH=("backend:=yolo" "perception_params:=$PP_YOLO" "model:=$MODEL_WH")
# method = base[+mod...]
BASE=${METHOD%%+*}; MODS=${METHOD#$BASE}; MODS=${MODS//+/ }
# diag_<method>: the same method with the diagnostic OpenVINS overlay (logging only), in its own method dir
if [[ $BASE == diag_* ]]; then BASE=${BASE#diag_}; DIAG=1; fi
case $BASE in
  openvins) LAUNCH=baseline.launch.py ;;
  savior_none) ARGS+=("backend:=none") ;;
  oracle_moving) ARGS+=("dataset:=warehouse_moving" "backend:=oracle_colormap" "roles_file:=$B/roles/warehouse_oracle_moving.yaml")
                 PSET="$ORACLE seg_right_topic=/cam1/segmentation_moving"; TOPICS="$TOPICS /cam0/segmentation_moving /cam1/segmentation_moving" ;;
  oracle_moving_warp) ARGS+=("dataset:=warehouse_moving" "backend:=oracle_colormap" "roles_file:=$B/roles/warehouse_oracle_moving.yaml")
                 PSET="$ORACLE compose.right_fallback=median"; TOPICS="$TOPICS /cam0/segmentation_moving" ;;
  oracle_moving_ext) ARGS+=("dataset:=warehouse_moving" "backend:=oracle_colormap" "roles_file:=$B/roles/warehouse_oracle_moving.yaml")
                 PSET="extension.enable=true tracker.enable=false compose.right_fallback=median"; TOPICS="$TOPICS /cam0/segmentation_moving" ;;   # + depth-adaptive band (192), warp right
  oracle_class_naive) ARGS+=("backend:=oracle_colormap" "roles_file:=$B/roles/warehouse_naive.yaml")
                 PSET="$ORACLE seg_right_topic=/cam1/segmentation"; TOPICS="$TOPICS /cam0/segmentation /cam1/segmentation" ;;
  yolo_naive) ARGS+=("${YOLO_WH[@]}" "roles_file:=$B/roles/warehouse_naive.yaml"); PSET="extension.enable=false tracker.enable=false compose.right_fallback=median" ;;
  yolo_p2) ARGS+=("${YOLO_WH[@]}" "roles_file:=$B/roles/warehouse.yaml"); PSET="$P2" ;;
  yolo_p4) ARGS+=("${YOLO_WH[@]}" "roles_file:=$B/roles/warehouse.yaml"); PSET="$P4" ;;
  yolo_p4_nointer) ARGS+=("${YOLO_WH[@]}" "roles_file:=$B/roles/warehouse.yaml"); PSET="$P4 gating.promote_contact=false" ;;
  yolo_p6) ARGS+=("${YOLO_WH[@]}" "roles_file:=$B/roles/warehouse.yaml"); PSET="$P4 motion.window_unveto_potential=true gating.max_depth=2" ;;   # post-hoc (offline_sens2)
  yolo_p4_noext) ARGS+=("${YOLO_WH[@]}" "roles_file:=$B/roles/warehouse.yaml"); PSET="$P4 extension.enable=false" ;;
  yolo_coco_person_p4) ARGS+=("backend:=yolo" "perception_params:=$PP_YOLO" "model:=$MODEL_COCO" "roles_file:=$B/roles/person_only.yaml"); PSET="$P4" ;;
  *) echo "unknown method $BASE"; exit 2 ;;
esac
for m in $MODS; do case $m in
  observe) OVSET="$OVSET dynamic_mask_threshold=256 dynamic_mask_relaxed_threshold=256" ;;
  nocompat) OVSET="${OVSET/dynamic_mask_upstream_compat=true/dynamic_mask_upstream_compat=false}" ;;   # SAVIOR front-end path on every frame
  *) echo "unknown mod $m"; exit 2 ;;
esac; done
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$(echo $PSET)")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8}
START=${START:-1}
OVL=""
if [[ -n "${DIAG:-}" ]]; then OVL="source $S/diag_ws/install/setup.bash;"; fi
RD=$WS/results/p6_warehouse/$SEQ/$METHOD
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; $OVL set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; ${DIAG:+export SAVIOR_DIAG_FILE=\$R/diag_updates.csv;} \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset p6_warehouse --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; i=\$((i+1)); done"
NAME="agentL_$(echo ${METHOD}_${SEQ} | tr '+' '_')_$DOM"
exec $WS/results/p6_warehouse/scripts/drun.sh $DOM $NAME bash -c "$INNER"
