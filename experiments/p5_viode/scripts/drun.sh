#!/usr/bin/env bash
# drun.sh <domain_id> <name> cmd...   : isolated throw-away SAVIOR container (no network, own ipc, thread caps)
set -euo pipefail
DOM=$1; NAME=$2; shift 2
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentI
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 "$@"
