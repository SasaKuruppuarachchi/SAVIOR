#!/usr/bin/env bash
# build the scratch copy (colcon, Release) inside the savior image
SCR=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge
docker run --rm --network none -v /tmp/claude-1002:/tmp/claude-1002 -e HOME=$SCR/home -e MAKEFLAGS=-j${J:-12} --name edge_build -w $SCR/ws savior:humble-cuda12.8 \
  bash -c "source /opt/ros/humble/setup.bash; colcon build --build-base $SCR/ws/build --install-base $SCR/ws/install --base-paths $SCR/ws/src --cmake-args -DCMAKE_BUILD_TYPE=Release $*"
