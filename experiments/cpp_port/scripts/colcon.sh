#!/usr/bin/env bash
# colcon.sh <sys|411> : build savior_perception_cpp + the scratch savior_bringup (overlay on the frozen workspace install)
SCR=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad
WS=/home/sasa/workspace/savior_ws
V=$1; shift
X=""
[[ $V == 411 ]] && X="-DSAVIOR_OPENCV_DIR=/opt/opencv-4.11/lib/cmake/opencv4"
exec docker run --rm --network none -v $WS:$WS:ro -v /tmp/claude-1002:/tmp/claude-1002 -e HOME=$SCR/edge/home -e MAKEFLAGS=-j${J:-16} \
  --name cpp_colcon_$V -w $SCR/ws savior-cpp:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; \
  colcon --log-base $SCR/ws/log_$V build --base-paths $SCR/ws/src/savior/savior_perception_cpp $SCR/ws/src/savior/savior_bringup ${EXTRA_PKGS:-} \
  --build-base $SCR/ws/build_$V --install-base $SCR/ws/install_$V --cmake-args -DCMAKE_BUILD_TYPE=Release -DSAVIOR_BUILD_PYTHON=ON $X $*"
