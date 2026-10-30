#!/usr/bin/env bash
# run_method.sh <seq> <method> <domain> -> results/p7/<seq>/<method>/run_XX (one isolated container, offsets in series)
# env: OFFSETS (default 10 offsets 0.0..1.8 s, all inside the 3 s hover), START (first run index, default 1), RATE (0.5)
# Methods: openvins | savior_none | oracle_moving_ext | yolo_naive | <any key of methods.json> (P7 variants; pset generated
# from scripts/variants.py by mkmethods.py, so offline (p7eval.py) and online parameters are identical).
# TUNING SET ONLY: refuses any sequence other than *_t1_* (held-out data must not be run by this agent).
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
[[ $SEQ == *_t1_* ]] || { echo "refusing $SEQ: tuning set is *_t1_* only"; exit 3; }
WS=/home/sasa/workspace/savior_ws
P=$WS/results/p7
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentN
B=$WS/src/savior/savior_bringup/config
CFG=$B/warehouse/estimator_config.yaml
BAG=$WS/data/warehouse/ros2_stereoseg/$SEQ
RATE=${RATE:-0.5}
MODEL_WH=$WS/models/warehouse/yolo26s-seg-warehouse.engine
PP_YOLO=$B/warehouse/savior_perception_yolo.yaml
LAUNCH=savior.launch.py
OVSET="deterministic_processing=true dynamic_mask_upstream_compat=true dynamic_mask_max_pending=0"
# stage F: OVTIME=1 -> OpenVINS per-update timing file (record_timing_information; no effect on the estimate),
# written inside the container to /tmp/ov_timing.txt and moved to run_XX/ov_timing.txt after each run
[[ -n "${OVTIME:-}" ]] && OVSET="$OVSET record_timing_information=true record_timing_filepath=/tmp/ov_timing.txt"
PSET=""
ARGS=()
TOPICS="/cam0/image_raw /cam1/image_raw /imu0 /tf_static"
YOLO_WH=("backend:=yolo" "perception_params:=$PP_YOLO" "model:=$MODEL_WH")
case $METHOD in
  openvins) LAUNCH=baseline.launch.py ;;
  savior_none) ARGS+=("backend:=none") ;;
  oracle_moving_ext) ARGS+=("dataset:=warehouse_moving" "backend:=oracle_colormap" "roles_file:=$B/roles/warehouse_oracle_moving.yaml")
                 PSET="extension.enable=true tracker.enable=false compose.right_fallback=median"; TOPICS="$TOPICS /cam0/segmentation_moving" ;;
  oracle_class_ext) ARGS+=("backend:=oracle_colormap" "roles_file:=$B/roles/warehouse_naive.yaml")   # P7 stage B: O-Cls+B (class-level GT masks + band, warp right = like-for-like with oracle_moving_ext)
                 PSET="extension.enable=true tracker.enable=false compose.right_fallback=median"; TOPICS="$TOPICS /cam0/segmentation" ;;
  *) J=$(python3 -c "import json,sys; d=json.load(open('$P/methods.json')); m=d['$METHOD']; print(m['roles']); print(m['pset'])") || { echo "unknown method $METHOD"; exit 2; }
     ROLES=$(echo "$J" | sed -n 1p); PSET=$(echo "$J" | sed -n 2p)
     ARGS+=("${YOLO_WH[@]}" "roles_file:=$B/roles/$ROLES.yaml") ;;
esac
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$(echo $PSET)")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8}
START=${START:-1}
DSN=${DSN:-p7}   # results/<DSN>/<seq>/<method>; stage F timing: DSN=p7/timing
RD=$WS/results/$DSN/$SEQ/$METHOD
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f /tmp/ov_timing.txt ]] && mv /tmp/ov_timing.txt \$R/ov_timing.txt; i=\$((i+1)); done"
NAME="agentN_$(echo ${METHOD}_${SEQ} | tr '+' '_')_$DOM"
exec $P/scripts/drun.sh $DOM $NAME bash -c "$INNER"
