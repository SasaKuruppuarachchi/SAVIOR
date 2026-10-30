#!/usr/bin/env bash
# run_method.sh <dataset:openloris|uhumans2> <seq> <method> <domain> <start_index> [-- extra launch args]
# env: OVSET_EXTRA="k=v ..." (OpenVINS overrides), PSET_EXTRA="k=v ..." (savior_node overrides), RATE, MODEL, METHOD_DIR (results name)
set -euo pipefail
DS=$1; SEQ=$2; METHOD=$3; DOM=$4; START=$5
shift 5
[[ "${1:-}" == "--" ]] && shift
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentF
SHARE=$WS/install/savior_bringup/share/savior_bringup
if [[ $DS == openloris ]]; then CFG=$SHARE/config/openloris_t265/estimator_config.yaml; GT=$WS/data/openloris/gt/$SEQ.txt
else CFG=$SHARE/config/uhumans2/estimator_config.yaml; GT=$WS/data/uhumans2/gt/$SEQ.txt; fi
RATE=${RATE:-0.5}
MODEL=${MODEL:-$WS/models/yolo26s-seg.engine}
LAUNCH=savior.launch.py
OVSET="deterministic_processing=true ${OVSET_EXTRA:-}"
PSET="${PSET_EXTRA:-}"
ARGS=()
case $METHOD in
  openvins*) LAUNCH=baseline.launch.py ;;
  savior_none*) ARGS+=("backend:=none") ;;
  savior_observe*) OVSET="$OVSET dynamic_mask_threshold=256 dynamic_mask_relaxed_threshold=256" ;;
  savior_full*) ;;
  savior_trk*) PSET="tracker.enable=true $PSET" ;;
  savior_cdo_off*) PSET="gating.enable=false $PSET" ;;
  savior_pp_off*) PSET="tracker.enable=false extension.enable=false $PSET" ;;
  naive_person*) ARGS+=("roles_file:=$SHARE/config/roles/person_only.yaml"); PSET="tracker.enable=false extension.enable=false $PSET" ;;
  *) echo "unknown method $METHOD"; exit 2 ;;
esac
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg model:=$MODEL)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$PSET")
fi
for a in "${ARGS[@]}" "$@"; do LA+=(--launch-arg "$a"); done
mkdir -p $S/roslog
OFFSETS=${OFFSETS:-0.0 0.2 0.4}
INNER="export ROS_LOG_DIR=$S/roslog; ${OVERLAY:+source $OVERLAY;} set -e; i=$START; for off in $OFFSETS; do savior-run --launch-file $LAUNCH --bag $WS/data/$DS/ros2/$SEQ --config $CFG -n 1 --start-index \$i --results-root $WS/results --dataset ${RESULTS_DATASET:-p2} --seq ${DS}_$SEQ --method ${METHOD_DIR:-$METHOD} --rate $RATE --domain-id $DOM --gt $GT --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}"); i=\$((i+1)); done"
exec $S/drun.sh $DOM agentF_${METHOD_DIR:-$METHOD}_${SEQ}_$DOM bash -c "$INNER"
