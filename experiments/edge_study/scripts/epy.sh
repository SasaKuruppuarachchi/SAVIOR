#!/usr/bin/env bash
# epy.sh <script.py> args... : python3 in the savior image with the EDGE scratch install + source first (no network)
WS=/home/sasa/workspace/savior_ws
SCR=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge
exec docker run --rm -i --network none --ipc private --shm-size 4g ${GPU---gpus all} ${CPUS:+--cpuset-cpus $CPUS} -v $WS:$WS -v /tmp/claude-1002:/tmp/claude-1002 -e HOME=$SCR/home \
  -e YOLO_CONFIG_DIR=$SCR/home/ultralytics -e MPLCONFIGDIR=$SCR/home/mpl -e OMP_NUM_THREADS=${NT:-4} -e OPENBLAS_NUM_THREADS=${NT:-4} -e SAVIOR_NUM_THREADS=${NT:-4} -e ANY=${ANY:-0} \
  ${NAME:+--name $NAME} -w /tmp savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $SCR/ws/install/setup.bash; export PYTHONPATH=$SCR/ws/src/savior/savior_perception:\$PYTHONPATH; python3 \"\$@\"" _ "$@"
