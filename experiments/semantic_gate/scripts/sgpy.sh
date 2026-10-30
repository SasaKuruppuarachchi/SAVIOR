#!/usr/bin/env bash
# sgpy.sh <cmd...>: run a command in the savior image (no network, no GPU) with the SG install sourced if it exists
# (results/semantic_gate/install), else ROS only; container name sg_py_*
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/sg
mkdir -p $S/home
exec docker run --rm -i --network none --ipc private -v $WS:$WS -v /tmp/claude-1002:/tmp/claude-1002 -e HOME=$S/home \
  -e MPLCONFIGDIR=$S/home/mpl -e OMP_NUM_THREADS=4 --name sg_py_$$_$RANDOM -w /tmp savior:humble-cuda12.8 \
  bash -c "source /opt/ros/humble/setup.bash; [[ -f $WS/results/semantic_gate/install/setup.bash ]] && source $WS/results/semantic_gate/install/setup.bash; \"\$@\"" _ "$@"
