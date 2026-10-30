#!/usr/bin/env bash
# offline.sh <seq> <out_name> [--set k=v ...]: perception_offline from SOURCE on an OpenLORIS bag
SEQ=$1; OUT=$2; shift 2
WS=/home/sasa/workspace/savior_ws; B=$WS/src/savior/savior_bringup
mkdir -p /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline
exec /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/drun.sh ${DOM:-228} agentH_off_${OUT}_$$ "cd /tmp && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$WS/src/savior/savior_perception:\$PYTHONPATH python3 $B/tools/perception_offline.py --bag $WS/data/openloris/ros2/$SEQ --params $WS/src/savior/savior_perception/config/default.yaml --params $B/config/openloris_t265/savior_perception.yaml --calib $B/config/openloris_t265/kalibr_imucam_chain.yaml --roles $B/config/roles/coco_indoor.yaml --set segmenter.model=$WS/models/yolo26s-seg.engine --set motion.static_mask_file=$B/config/openloris_t265/mask_t265_cam0.png --stats /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline/$OUT.jsonl $*"
