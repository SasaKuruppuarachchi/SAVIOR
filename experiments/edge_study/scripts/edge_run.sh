#!/usr/bin/env bash
# edge_run.sh <seq> <method> <domain> -> results/edge_study/runs/<seq>/<method>/run_XX (one isolated container, offsets in series)
# Same protocol as results/p7/scripts/run_method.sh (rate 0.5, mask_policy wait, 30 s timeout, deterministic, 10 offsets) but
# against the EDGE SCRATCH install (never the workspace install). Methods: edge_methods.json (edge_mkmethods.py).
# env: OFFSETS, START, RATE (0.5), OVTIME=1 (ov timing file), CPUS (docker --cpuset-cpus), DSN (edge_study/runs)
# TUNING SET ONLY: refuses any sequence other than *_t1_*.
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
[[ $SEQ == *_t1_* ]] || { echo "refusing $SEQ: tuning set is *_t1_* only"; exit 3; }
WS=/home/sasa/workspace/savior_ws
SCR=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge
B=$WS/src/savior/savior_bringup/config
CFG=$B/warehouse/estimator_config.yaml
BAG=$WS/data/warehouse/ros2_stereoseg/$SEQ
RATE=${RATE:-0.5}
PP_YOLO=$B/warehouse/savior_perception_yolo.yaml
LAUNCH=savior.launch.py
OVSET="deterministic_processing=true dynamic_mask_upstream_compat=true dynamic_mask_max_pending=0"
[[ -n "${OVTIME:-}" ]] && OVSET="$OVSET record_timing_information=true record_timing_filepath=/tmp/ov_timing.txt"
TOPICS="/cam0/image_raw /cam1/image_raw /imu0 /tf_static"
ARGS=()
PSET=""
if [[ $METHOD == openvins* ]]; then
  LAUNCH=baseline.launch.py
else
  J=$(python3 -c "import json; m=json.load(open('$SCR/edge_methods.json'))['$METHOD']; print(m['roles']); print(m['pset']); print(m['ov']); print(m['model'])") || { echo "unknown method $METHOD"; exit 2; }
  ROLES=$(echo "$J" | sed -n 1p); PSET=$(echo "$J" | sed -n 2p); OVX=$(echo "$J" | sed -n 3p); MODEL=$(echo "$J" | sed -n 4p)
  [[ -n "${OVX// }" ]] && OVSET="$OVSET $OVX"
  ARGS+=("backend:=yolo" "perception_params:=$PP_YOLO" "model:=$MODEL" "roles_file:=$B/roles/$ROLES.yaml")
fi
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$(echo $PSET)")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8}
START=${START:-1}
DSN=${DSN:-edge_study/runs}
RD=$WS/results/$DSN/$SEQ/$METHOD
INNER="export ROS_LOG_DIR=$SCR/roslog; source /opt/ros/humble/setup.bash; source $SCR/ws/install/setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f /tmp/ov_timing.txt ]] && mv /tmp/ov_timing.txt \$R/ov_timing.txt; i=\$((i+1)); done"
NAME="edge_$(echo ${METHOD}_${SEQ} | tr '+' '_')_$DOM"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g ${CPUS:+--cpuset-cpus $CPUS} \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$SCR/home/ultralytics -e MPLCONFIGDIR=$SCR/home/mpl \
  -e HOME=$SCR/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "$INNER"
