#!/usr/bin/env bash
# offline_u.sh <seq> <out_name> [args]: perception_offline from SOURCE on a uHumans2 bag (YOLO backend)
SEQ=$1; OUT=$2; shift 2
WS=/home/sasa/workspace/savior_ws; B=$WS/src/savior/savior_bringup
mkdir -p /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline
exec /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/drun.sh ${DOM:-227} agentH_offu_${OUT}_$$ "cd /tmp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WS/src/savior/savior_perception:\$PYTHONPATH python3 $B/tools/perception_offline.py --dataset uhumans2 --bag $WS/data/uhumans2/ros2/$SEQ --params $WS/src/savior/savior_perception/config/default.yaml --params $B/config/uhumans2/savior_perception.yaml --calib $B/config/uhumans2/kalibr_imucam_chain.yaml --roles $B/config/roles/coco_indoor.yaml --set segmenter.backend=yolo --set tracker.enable=false --set segmenter.model=$WS/models/yolo26s-seg.engine --stats /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline/$OUT.jsonl $*"
