set -e
for seq in hall_t1_L3 aisles_t1_L2; do
  (source /home/sasa/workspace/savior_ws/install/setup.bash; python3 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/jv/pkg/scripts/lib/pipe_dump.py --seq $seq --engine /home/sasa/workspace/savior_ws/models/warehouse/yolo26s-seg-warehouse.engine --out /home/sasa/workspace/savior_ws/results/jetson_validation/raw/server_pipe_masks/server_main_$seq.npz) > /home/sasa/workspace/savior_ws/results/jetson_validation/raw/server_pipe_masks/dump_main_$seq.log 2>&1
  (source /home/sasa/workspace/savior_ws/install/setup.bash; source /home/sasa/workspace/savior_ws/frozen_edge/install/setup.bash; python3 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/jv/pkg/scripts/lib/pipe_dump.py --seq $seq --engine /home/sasa/workspace/savior_ws/frozen_edge/models/yolo26n-seg-warehouse-672.engine --edge --out /home/sasa/workspace/savior_ws/results/jetson_validation/raw/server_pipe_masks/server_edge_$seq.npz) > /home/sasa/workspace/savior_ws/results/jetson_validation/raw/server_pipe_masks/dump_edge_$seq.log 2>&1
done
echo ALLDONE
