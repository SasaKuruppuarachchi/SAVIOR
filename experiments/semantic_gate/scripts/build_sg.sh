#!/usr/bin/env bash
# build_sg.sh : colcon build of src/savior (all packages: OpenVINS fork + savior_*) into the SG prefix
# results/semantic_gate/{build,install,log} (copies, no --symlink-install, Release, as the frozen workspace install/).
# Never touches install/, build/, frozen_edge/ or ref/. Container sg_colcon.
set -euo pipefail
WS=/home/sasa/workspace/savior_ws
SG=$WS/results/semantic_gate
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/sg
mkdir -p $S/home
exec docker run --rm --network none -v $WS:$WS -v /tmp/claude-1002:/tmp/claude-1002 -e HOME=$S/home -e MAKEFLAGS=-j${J:-12} \
  --name sg_colcon -w $SG savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; \
  colcon --log-base $SG/log build --base-paths $WS/src/savior --build-base $SG/build --install-base $SG/install \
  --cmake-args -DCMAKE_BUILD_TYPE=Release $*"
