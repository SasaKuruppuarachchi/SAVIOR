#!/usr/bin/env bash
# cpp_run.sh <seq> <method> <domain> -> results/cpp_port/runs/<seq>/<method>/run_XX (one isolated container, offsets in series)
# Same protocol as results/p7/scripts/run_method.sh / results/edge_study/scripts/edge_run.sh (rate 0.5, mask_policy wait,
# 30 s mask timeout, deterministic OpenVINS, 10 start offsets) with RUNNER/install override: the frozen workspace install
# (OpenVINS fork, savior_perception, savior_eval) + the C++ port overlay (savior_perception_cpp, scratch savior_bringup with
# perception_impl; underlay per method: frozen workspace install or frozen_edge/install). Methods: $SCR/cpp/methods.json (impl python|cpp, variant sys = system OpenCV 4.5.4 | 411 = OpenCV 4.11).
# env: OFFSETS, START, RATE, CPUS (--cpuset-cpus), DSN (cpp_port/runs), OVTIME=1. TUNING SET ONLY (*_t1_*).
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
[[ $SEQ == *_t1_* ]] || { echo "refusing $SEQ: tuning set is *_t1_* only"; exit 3; }
WS=/home/sasa/workspace/savior_ws
SCR=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad
B=$WS/src/savior/savior_bringup/config
CFG=$B/warehouse/estimator_config.yaml
BAG=$WS/data/warehouse/ros2_stereoseg/$SEQ
RATE=${RATE:-0.5}
PP_YOLO=$B/warehouse/savior_perception_yolo.yaml
OVSET="deterministic_processing=true dynamic_mask_upstream_compat=true dynamic_mask_max_pending=0"
[[ -n "${OVTIME:-}" ]] && OVSET="$OVSET record_timing_information=true record_timing_filepath=/tmp/ov_timing.txt"
TOPICS="/cam0/image_raw /cam1/image_raw /imu0 /tf_static"
J=$(python3 -c "import json; m=json.load(open('$SCR/cpp/methods.json'))['$METHOD']; print(m['roles']); print(m['pset']); print(m['ov']); print(m['model']); print(m['impl']); print(m['variant']); print(m.get('underlay', '$WS/install'))") || { echo "unknown method $METHOD"; exit 2; }
ROLES=$(echo "$J" | sed -n 1p); PSET=$(echo "$J" | sed -n 2p); OVX=$(echo "$J" | sed -n 3p); MODEL=$(echo "$J" | sed -n 4p)
IMPL=$(echo "$J" | sed -n 5p); VAR=$(echo "$J" | sed -n 6p); UNDER=$(echo "$J" | sed -n 7p)
[[ -n "${OVX// }" ]] && OVSET="$OVSET $OVX"
ARGS=("backend:=yolo" "perception_params:=$PP_YOLO" "model:=$MODEL" "roles_file:=$B/roles/$ROLES.yaml" "perception_impl:=$IMPL")
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
[[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$(echo $PSET)")
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8}
START=${START:-1}
DSN=${DSN:-cpp_port/runs}
RD=$WS/results/$DSN/$SEQ/$METHOD
INNER="export ROS_LOG_DIR=$SCR/cpp/roslog; source /opt/ros/humble/setup.bash; source $UNDER/setup.bash; source $SCR/ws/install_$VAR/local_setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file savior.launch.py --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f /tmp/ov_timing.txt ]] && mv /tmp/ov_timing.txt \$R/ov_timing.txt; i=\$((i+1)); done"
NAME="cppport_$(echo ${METHOD}_${SEQ} | tr '+' '_')_$DOM"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g ${CPUS:+--cpuset-cpus $CPUS} \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$SCR/cpp/home/ultralytics -e MPLCONFIGDIR=$SCR/cpp/home/mpl \
  -e HOME=$SCR/cpp/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior-cpp:humble-cuda12.8 bash -c "$INNER"
