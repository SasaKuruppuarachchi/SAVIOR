#!/usr/bin/env bash
# drun.sh <domain_id> <name> "cmd": isolated throw-away SAVIOR container (no network, own ipc), agentH overlay ONLY
# env OVERLAY2: optional extra setup.bash sourced after $SCR/install (versioned python-only overlays)
set -euo pipefail
DOM=$1; NAME=$2; shift 2
WS=/home/sasa/workspace/savior_ws
SCR=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH
O2=${OVERLAY2:-}
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e _SAVIOR_ENV_DONE=1 -e SAVIOR_MODELS_DIR=$WS/models -e YOLO_CONFIG_DIR=$WS/.cache/ultralytics \
  -e TORCH_HOME=$WS/.cache/torch -e MPLCONFIGDIR=$SCR/home/mpl -e HOME=$SCR/home \
  -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; if [[ -f $SCR/install/setup.bash ]]; then source $SCR/install/setup.bash; fi; if [[ -n '$O2' ]]; then source $O2; fi; $*"
