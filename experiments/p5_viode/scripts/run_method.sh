#!/usr/bin/env bash
# run_method.sh <seq: env_level> <method> <domain>   -> results/p5_viode/<seq>/<method>/run_XX (one container, offsets in series)
# env: OFFSETS (default 10 offsets "0.0 0.2 ... 1.8"), START (run index of the first offset, default 1), RATE (0.5),
#      DIAG=1: diagnostic OpenVINS overlay (feature-fate log run_XX/diag_updates.csv)
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
ENV=${SEQ%_*}
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentI
B=$WS/src/savior/savior_bringup/config
CFG=$B/viode/estimator_config.yaml
GT=$WS/data/viode/gt/$SEQ.txt
BAG=$WS/data/viode/ros2/$SEQ
RATE=${RATE:-0.5}
MODEL=$WS/models/yolo26s-seg.engine
CMAP=$B/oracle/viode_${ENV}_colormap.yaml
LAUNCH=savior.launch.py
OVSET="deterministic_processing=true dynamic_mask_upstream_compat=true"
PSET=""
ARGS=()
TOPICS="/cam0/image_raw /cam1/image_raw /imu0"
P4="motion.enable=true gating.link_depth=contact gating.max_noise_m=0.5 tracker.enable=false extension.enable=true motion.still_policy=unmask compose.right_fallback=median"
ORACLE="extension.enable=false tracker.enable=false segmenter.colormap_file=$CMAP"
# method = base[+mod...]
BASE=${METHOD%%+*}; MODS=${METHOD#$BASE}; MODS=${MODS//+/ }
case $BASE in
  openvins) LAUNCH=baseline.launch.py ;;
  diag_openvins) LAUNCH=baseline.launch.py ;;    # with DIAG=1: diagnostic overlay (feature fates)
  savior_none) ARGS+=("backend:=none") ;;
  oracle_dynamic) ARGS+=("backend:=oracle_colormap" "roles_file:=$B/roles/viode_oracle_dynamic.yaml"); PSET="$ORACLE seg_right_topic=/cam1/segmentation"
                  TOPICS="$TOPICS /cam0/segmentation /cam1/segmentation" ;;
  oracle_all_vehicles) ARGS+=("backend:=oracle_colormap" "roles_file:=$B/roles/viode_oracle_all_vehicles.yaml"); PSET="$ORACLE seg_right_topic=/cam1/segmentation"
                  TOPICS="$TOPICS /cam0/segmentation /cam1/segmentation" ;;
  oracle_dynamic_warp) ARGS+=("backend:=oracle_colormap" "roles_file:=$B/roles/viode_oracle_dynamic.yaml"); PSET="$ORACLE compose.right_fallback=median"
                  TOPICS="$TOPICS /cam0/segmentation" ;;
  oracle_observe) ARGS+=("backend:=oracle_colormap" "roles_file:=$B/roles/viode_oracle_all_vehicles.yaml"); PSET="$ORACLE seg_right_topic=/cam1/segmentation"
                  TOPICS="$TOPICS /cam0/segmentation /cam1/segmentation"; OVSET="$OVSET dynamic_mask_threshold=256 dynamic_mask_relaxed_threshold=256" ;;
  yolo_naive) ARGS+=("backend:=yolo" "roles_file:=$B/roles/viode_vehicles_dynamic.yaml"); PSET="extension.enable=false tracker.enable=false" ;;
  yolo_full_p2) ARGS+=("backend:=yolo" "roles_file:=$B/roles/viode_vehicles_dynamic.yaml"); PSET="tracker.enable=false" ;;
  yolo_p4_dyn) ARGS+=("backend:=yolo" "roles_file:=$B/roles/viode_vehicles_dynamic.yaml"); PSET="$P4" ;;
  yolo_p4_pot) ARGS+=("backend:=yolo" "roles_file:=$B/roles/viode_vehicles_potential.yaml"); PSET="$P4" ;;
  *) echo "unknown method $BASE"; exit 2 ;;
esac
for m in $MODS; do case $m in
  fast15) OVSET="$OVSET fast_threshold=15" ;;
  observe) OVSET="$OVSET dynamic_mask_threshold=256 dynamic_mask_relaxed_threshold=256" ;;
  late) ;;                                     # label only: start offsets after the rotation-only hover (job offsets)
  slam0) OVSET="$OVSET max_slam=0" ;;
  dminsdeg) OVSET="$OVSET init_dyn_min_deg=30.0" ;;
  *) echo "unknown mod $m"; exit 2 ;;
esac; done
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg model:=$MODEL --launch-arg mask_timeout_ms:=30000)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$(echo $PSET)")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8}
START=${START:-1}
OVL=""
if [[ -n "${DIAG:-}" ]]; then OVL="source $S/diag_ws/install/setup.bash;"; fi
RD=$WS/results/p5_viode/$SEQ/$METHOD
TEMPLATE="ros2 launch $S/launch/{launch_file} config:={config} bag:={bag} output:={output}"
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; $OVL set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; ${DIAG:+export SAVIOR_DIAG_FILE=\$R/diag_updates.csv;} \
  savior-run --cmd-template '$TEMPLATE' --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset p5_viode --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; i=\$((i+1)); done"
NAME="agentI_$(echo ${METHOD}_${SEQ} | tr '+' '_')_$DOM"
exec $WS/results/p5_viode/scripts/drun.sh $DOM $NAME bash -c "$INNER"
