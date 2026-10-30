#!/usr/bin/env bash
# run_ov.sh <seq> <variant> : stock OpenVINS (baseline.launch.py, no perception) with results/ov_diag/configs/<variant>
# -> results/ov_diag/runs/<seq>/<variant>/run_XX. One isolated container, 2 lanes x 5 offsets in parallel (own ROS domains).
# Same launch settings as results/p7/scripts/run_method.sh 'openvins' (deterministic, rate 0.5, P6/P7 offsets 0.0..1.8 s).
# TUNING SET ONLY (*_t1_*).
set -euo pipefail
SEQ=$1; VAR=$2
[[ $SEQ == *_t1_* ]] || { echo "refusing $SEQ: t1 only"; exit 3; }
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/ovdiag
CFG=$WS/results/ov_diag/configs/$VAR/estimator_config.yaml
[[ -f $CFG ]] || { echo "no config $CFG"; exit 2; }
BAG=$WS/data/warehouse/ros2_stereoseg/$SEQ
RATE=0.5
OVSET="deterministic_processing=true dynamic_mask_upstream_compat=true dynamic_mask_max_pending=0"
TOPICS="/cam0/image_raw /cam1/image_raw /imu0 /tf_static"
OFFS=(0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8)
lane() {  # lane <domain> <indices...>
  local dom=$1; shift
  local cmd=""
  for i in "$@"; do
    local off=${OFFS[$((i-1))]}
    cmd="$cmd savior-run --launch-pkg savior_bringup --launch-file baseline.launch.py --bag $BAG --config $CFG -n 1 --start-index $i \
 --results-root $WS/results --dataset ov_diag/runs --seq $SEQ --method $VAR --rate $RATE --domain-id $dom --cooldown 1 \
 --launch-arg start_offset:=$off --launch-arg rate:=$RATE --launch-arg feature_stats:=auto \
 --launch-arg 'ov_set:=$OVSET' --launch-arg 'topics:=$TOPICS' > /dev/null 2>&1 || echo 'run $i failed';"
  done
  echo "$cmd"
}
L1=$(lane 11 1 2 3 4 5); L2=$(lane 12 6 7 8 9 10)
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; ( $L1 ) & ( $L2 ) & wait"
NAME="ovdiag_${VAR}_${SEQ}"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 -w $WS savior:humble-cuda12.8 bash -c "$INNER"
