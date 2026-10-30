#!/usr/bin/env bash
# convert_stereoseg.sh seq... : re-convert raw sequences with --seg-right (adds /cam1/segmentation(_moving)) into
# data/warehouse/ros2_stereoseg/<seq>; GT is written to scratch and compared with data/warehouse/gt (must be identical)
WS=/home/sasa/workspace/savior_ws; S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentL
for q in "$@"; do
  python3 -I $WS/src/savior/savior_datasets/warehouse/tools/to_ros2.py --raw $WS/data/warehouse/raw/$q \
    --out $WS/data/warehouse/ros2_stereoseg/$q --gt $S/gtcopy/$q.txt --seg-right && cmp $S/gtcopy/$q.txt $WS/data/warehouse/gt/$q.txt && echo "GT identical $q"
done
