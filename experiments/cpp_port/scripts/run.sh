#!/usr/bin/env bash
# run.sh <build subdir> <script> args... : python3 in savior-cpp with the scratch savior_perception + the C++ module
SCR=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad
WS=/home/sasa/workspace/savior_ws
BD=$1; shift
exec docker run --rm -i --network none --ipc private ${GPU---gpus all} ${CPUS:+--cpuset-cpus $CPUS} -v $WS:$WS:ro -v /tmp/claude-1002:/tmp/claude-1002 \
  -e HOME=$SCR/edge/home -e YOLO_CONFIG_DIR=$SCR/edge/home/ultralytics -e PYTHONDONTWRITEBYTECODE=1 \
  -e OMP_NUM_THREADS=${NT:-1} -e OPENBLAS_NUM_THREADS=${NT:-1} -e MKL_NUM_THREADS=${NT:-1} -e OPENCV_FOR_THREADS_NUM=4 \
  ${NAME:+--name $NAME} -w /tmp ${IMG:-savior-cpp:humble-cuda12.8} bash -c "source /opt/ros/humble/setup.bash; export PYTHONPATH=$SCR/cppbuild/$BD:$SCR/ws/src/savior/savior_perception:\$PYTHONPATH; export LD_LIBRARY_PATH=$SCR/cppbuild/$BD:/opt/opencv-4.11/lib:/opt/opencv-4.8/lib:\$LD_LIBRARY_PATH; python3 \"\$@\"" _ "$@"
