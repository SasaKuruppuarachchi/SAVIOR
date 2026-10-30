#!/usr/bin/env bash
# py.sh <script.py|-c code> args... : python3 in the savior image (workspace install sourced, no network, no GPU)
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentL
exec docker run --rm -i --network none --ipc private -v $WS:$WS -v /tmp/claude-1002:/tmp/claude-1002 -e HOME=$S/home \
  -e MPLCONFIGDIR=$S/home/mpl -e OMP_NUM_THREADS=4 -e OPENBLAS_NUM_THREADS=4 -w /tmp savior:humble-cuda12.8 bash -c 'source /opt/ros/humble/setup.bash; source '$WS'/install/setup.bash; python3 "$@"' _ "$@"
