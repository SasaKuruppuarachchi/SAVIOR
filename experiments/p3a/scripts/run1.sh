#!/usr/bin/env bash
# run1.sh <seq> <method> <offset_index 1..5> <domain>  : one P3a run (one bag start offset) in an isolated container
# env: OVERLAY (extra setup.bash sourced after the workspace install, e.g. the diagnostic OpenVINS build), DIAG_DIR
set -euo pipefail
SEQ=$1; METHOD=$2; IDX=$3; DOM=$4
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentG
P3=$WS/results/p3a
SHARE=$WS/install/savior_bringup/share/savior_bringup
CFG=$SHARE/config/uhumans2/estimator_config.yaml
GT=$WS/data/uhumans2/gt/$SEQ.txt
OFFS=(0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8)
OFF=${OFFS[$((IDX-1))]}
mkdir -p $P3/locks
mkdir $P3/locks/${SEQ}_${METHOD}_${IDX} 2>/dev/null || { echo "locked: $SEQ $METHOD $IDX"; exit 0; }
RATE=${RATE:-0.5}
MODEL=$WS/models/yolo26s-seg.engine
PERSON=$SHARE/config/roles/person_only.yaml
CMAPP=$P3/config/uhumans2_colormap_person.yaml
LAUNCH=savior.launch.py
OVSET="deterministic_processing=true"
PSET=""
ARGS=()
case $METHOD in
  openvins|diag_openvins) LAUNCH=baseline.launch.py ;;
  savior_none) ARGS+=("backend:=none") ;;
  oracle_person) ARGS+=("backend:=oracle_colormap" "roles_file:=$PERSON"); PSET="tracker.enable=false extension.enable=false segmenter.colormap_file=$CMAPP" ;;
  oracle_person_ext) ARGS+=("backend:=oracle_colormap" "roles_file:=$PERSON"); PSET="tracker.enable=false segmenter.colormap_file=$CMAPP" ;;
  oracle_person_after_init) ARGS+=("backend:=oracle_colormap" "roles_file:=$PERSON"); PSET="tracker.enable=false extension.enable=false segmenter.colormap_file=$CMAPP"
                            OVSET="$OVSET dynamic_mask_after_init=true" ;;
  oracle_observe|diag_oracle_observe) ARGS+=("backend:=oracle_colormap" "roles_file:=$PERSON"); PSET="tracker.enable=false extension.enable=false segmenter.colormap_file=$CMAPP"
                  OVSET="$OVSET dynamic_mask_threshold=256 dynamic_mask_relaxed_threshold=256" ;;
  oracle_person_diag) ARGS+=("backend:=oracle_colormap" "roles_file:=$PERSON"); PSET="tracker.enable=false extension.enable=false segmenter.colormap_file=$CMAPP" ;;
  yolo_full) ARGS+=("backend:=yolo"); PSET="tracker.enable=false" ;;
  yolo_naive) ARGS+=("backend:=yolo" "roles_file:=$PERSON"); PSET="tracker.enable=false extension.enable=false segmenter.colormap_file=$CMAPP" ;;
  *) echo "unknown method $METHOD"; exit 2 ;;
esac
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg start_offset:=$OFF --launch-arg mask_timeout_ms:=${MASK_TIMEOUT:-30000})
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg model:=$MODEL)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$PSET")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
mkdir -p $S/roslog
RUNDIR=$P3/uhumans2_$SEQ/$METHOD/run_$(printf %02d $IDX)
DIAGENV=""
if [[ -n "${OVERLAY:-}" ]]; then DIAGENV="export SAVIOR_DIAG_FILE=$RUNDIR/diag_updates.csv;"; fi
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; ${OVERLAY:+source $OVERLAY;} $DIAGENV set -e; mkdir -p $RUNDIR; savior-run --launch-file $LAUNCH --bag $WS/data/uhumans2/ros2/$SEQ --config $CFG -n 1 --start-index $IDX --results-root $WS/results --dataset p3a --seq uhumans2_$SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 $(printf '%q ' "${LA[@]}")"
exec /home/sasa/workspace/savior_ws/results/p3a/scripts/drun.sh $DOM agentG_${METHOD}_${SEQ}_$IDX bash -c "$INNER"
