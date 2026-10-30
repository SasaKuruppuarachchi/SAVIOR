#!/usr/bin/env bash
# gpy.sh <script.py|-c code> args... : python3 in the savior image with GPU (workspace install sourced, no network)
# env SRC=1: put src/savior/savior_perception first on PYTHONPATH (test uninstalled code)
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentN
PP=""; [[ -n "${SRC:-}" ]] && PP="export PYTHONPATH=$WS/src/savior/savior_perception:\$PYTHONPATH;"
exec docker run --rm -i --network none --ipc private --shm-size 4g ${GPU---gpus all} -v $WS:$WS -v /tmp/claude-1002:/tmp/claude-1002 -e HOME=$S/home \
  -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl -e OMP_NUM_THREADS=${NT:-4} -e OPENBLAS_NUM_THREADS=${NT:-4} -e SAVIOR_NUM_THREADS=${NT:-4} \
  ${NAME:+--name $NAME} -w /tmp savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; $PP python3 \"\$@\"" _ "$@"
