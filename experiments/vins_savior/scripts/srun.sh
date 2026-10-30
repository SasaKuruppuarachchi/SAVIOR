#!/usr/bin/env bash
# srun.sh <name> <install dir> cmd... : isolated throw-away savior container (GPU, no network), install sourced,
# same thread caps as results/p7/scripts/drun.sh / m2b run_m2b.sh (the online runs).
set -euo pipefail
NAME=$1; INSTALL=$2; shift 2
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/vs
mkdir -p $S/home
CMD=$(printf '%q ' "$@")
exec docker run --rm --init -i --name "vs_$NAME" --network none --ipc private --shm-size 8g --user "$(id -u):$(id -g)" \
  -v $WS:$WS -v /tmp/claude-1002:/tmp/claude-1002 -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=0 -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl -e HOME=$S/home -e ROS_LOG_DIR=$S/roslog \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $INSTALL/setup.bash; $CMD"
