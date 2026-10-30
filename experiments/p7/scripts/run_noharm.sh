#!/usr/bin/env bash
# run_noharm.sh <seq> <method> <domain> -> results/p7/noharm/<seq>/<method>/run_XX (P7 stage D, one isolated container)
# ONLY the two no-harm sequences approved in PLAN_approved.txt: openloris_cafe1-1 and uhumans2_office_s1_06h.
# Methods: openvins | savior_none (empty-mask control) | yolo_naive (COCO person only, no band, no tracker) |
#          <main> (any key of methods.json: its pset with COCO roles (coco_indoor) + selective.prior_static_classes=COCO_PRIOR)
# env: OFFSETS (default 10 offsets 0.0..1.8 s), START (1), RATE (0.5)
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
case $SEQ in
  openloris_cafe1-1) DS=openloris; RAW=cafe1-1; CFGD=openloris_t265 ;;
  uhumans2_office_s1_06h) DS=uhumans2; RAW=office_s1_06h; CFGD=uhumans2 ;;
  *) echo "refusing $SEQ: no-harm set is openloris_cafe1-1 / uhumans2_office_s1_06h only"; exit 3 ;;
esac
WS=/home/sasa/workspace/savior_ws
P=$WS/results/p7
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentN
B=$WS/src/savior/savior_bringup/config
CFG=$B/$CFGD/estimator_config.yaml
BAG=$WS/data/$DS/ros2/$RAW
GT=$WS/data/$DS/gt/$RAW.txt
RATE=${RATE:-0.5}
MODEL=$WS/models/yolo26s-seg.engine
COCO_PRIOR=${COCO_PRIOR:-chair,suitcase,backpack,handbag,cart}
LAUNCH=savior.launch.py
OVSET="deterministic_processing=true dynamic_mask_upstream_compat=true dynamic_mask_max_pending=0"
PSET=""
ARGS=()
case $METHOD in
  openvins) LAUNCH=baseline.launch.py ;;
  savior_none) ARGS+=("backend:=none") ;;
  yolo_naive) ARGS+=("backend:=yolo" "model:=$MODEL" "roles_file:=$B/roles/person_only.yaml")
              PSET="extension.enable=false tracker.enable=false compose.right_fallback=median stats_compact=true segmenter.fast_masks=true" ;;
  *) PSET=$(python3 -c "import json; d=json.load(open('$P/methods.json')); print(d['$METHOD']['pset'])") || { echo "unknown method $METHOD"; exit 2; }
     PSET=$(echo "$PSET" | sed -E "s/selective.prior_static_classes=[^ ]+/selective.prior_static_classes=$COCO_PRIOR/")
     ARGS+=("backend:=yolo" "model:=$MODEL" "roles_file:=$B/roles/coco_indoor.yaml") ;;
esac
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$(echo $PSET)")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8}
START=${START:-1}
RD=$P/noharm/$SEQ/$METHOD
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $P \
  --dataset noharm --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --gt $GT --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; i=\$((i+1)); done"
NAME="agentN_nh_$(echo ${METHOD}_${SEQ} | tr '+' '_')_$DOM"
exec $P/scripts/drun.sh $DOM $NAME bash -c "$INNER"
