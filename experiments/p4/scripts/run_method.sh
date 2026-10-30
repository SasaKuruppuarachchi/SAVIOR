#!/usr/bin/env bash
# run_method.sh <dataset:openloris|uhumans2> <seq> <method> <domain>   (agentH overlay; results/p4/<ds>_<seq>/<method>/run_XX)
# env: OFFSETS (default "0.0 0.2 0.4 0.6 0.8"), RATE (0.5), START (1)
set -euo pipefail
DS=$1; SEQ=$2; METHOD=$3; DOM=$4
WS=/home/sasa/workspace/savior_ws
SCR=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH
SHARE=$SCR/install/savior_bringup/share/savior_bringup
if [[ $DS == openloris ]]; then CFG=$SHARE/config/openloris_t265/estimator_config.yaml; GT=$WS/data/openloris/gt/$SEQ.txt
else CFG=$SHARE/config/uhumans2/estimator_config.yaml; GT=$WS/data/uhumans2/gt/$SEQ.txt; fi
RATE=${RATE:-0.5}
MODEL=$WS/models/yolo26s-seg.engine
LAUNCH=savior.launch.py
OVSET="deterministic_processing=true"
PSET=""
ARGS=()
[[ $DS == uhumans2 ]] && { ARGS+=("backend:=yolo"); PSET="tracker.enable=false"; }
MOT="motion.enable=true"
GATE="gating.link_depth=contact gating.max_noise_m=0.5"
FAST="fast_threshold=15"
# method = base[+mod+mod...]; mods are applied left to right
BASE=${METHOD%%+*}; MODS=${METHOD#$BASE}; MODS=${MODS//+/ }
case $BASE in
  openvins) LAUNCH=baseline.launch.py ;;
  none) ARGS+=("backend:=none") ;;
  full) ;;                                    # P2 savior_full (defaults of the dataset config)
  naive) ARGS+=("roles_file:=$SHARE/config/roles/person_only.yaml"); PSET="$PSET tracker.enable=false extension.enable=false" ;;
  *) echo "unknown base $BASE"; exit 2 ;;
esac
for m in $MODS; do case $m in
  mot) PSET="$PSET $MOT" ;;                                    # motion evidence (i)+(ii)+(iii)
  still) PSET="$PSET $MOT motion.promote_moving=false motion.veto_static=false" ;;   # (i) only
  noveto) PSET="$PSET motion.veto_static=false" ;;
  noprom) PSET="$PSET motion.promote_moving=false" ;;
  nostill) PSET="$PSET motion.use_still=false" ;;
  band) PSET="$PSET motion.still_policy=band" ;;
  gate) PSET="$PSET $GATE" ;;                                  # contact-depth gate + noise cap
  cap) PSET="$PSET gating.max_noise_m=0.5" ;;
  contact) PSET="$PSET gating.link_depth=contact" ;;
  noext) PSET="$PSET extension.enable=false" ;;
  trk) PSET="$PSET tracker.enable=true" ;;
  trkego) PSET="$PSET tracker.enable=true tracker.motion_model=ego" ;;
  icore) OVSET="$OVSET dynamic_mask_init_policy=core" ;;
  inone) OVSET="$OVSET dynamic_mask_init_policy=none" ;;
  irelax) OVSET="$OVSET dynamic_mask_init_policy=relax" ;;
  fast15) OVSET="$OVSET fast_threshold=15" ;;
  fast20) OVSET="$OVSET fast_threshold=20" ;;
  grid8) OVSET="$OVSET grid_x=8 grid_y=8" ;;
  mpx10) OVSET="$OVSET min_px_dist=10" ;;
  fast10) OVSET="$OVSET fast_threshold=10" ;;
  compat) OVSET="$OVSET dynamic_mask_upstream_compat=true" ;;
  rfb) PSET="$PSET compose.right_fallback=median" ;;
  pts200) OVSET="$OVSET num_pts=200" ;;
  *) echo "unknown mod $m"; exit 2 ;;
esac; done
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg model:=$MODEL)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$(echo $PSET)")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8}
START=${START:-1}
INNER="export ROS_LOG_DIR=$SCR/roslog; set -e; i=$START; for off in $OFFSETS; do savior-run --launch-file $LAUNCH --bag $WS/data/$DS/ros2/$SEQ --config $CFG -n 1 --start-index \$i --results-root $WS/results --dataset p4 --seq ${DS}_$SEQ --method $METHOD --rate $RATE --domain-id $DOM --gt $GT --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}"); i=\$((i+1)); done"
NAME="agentH_$(echo ${METHOD}_${SEQ} | tr '+' '_')_$DOM"
exec $SCR/drun.sh $DOM $NAME "$INNER"
