#!/usr/bin/env bash
# waits for a quiet machine, then runs all timing measurements sequentially
while true; do
  n=$(docker ps --format '{{.Names}}' | grep -v agipix | wc -l); l=$(cut -d' ' -f1 /proc/loadavg)
  if [ "$n" -eq 0 ] && python3 -c "import sys; sys.exit(0 if $l < 3.0 else 1)"; then break; fi
  sleep 60
done
echo "$(date) quiet: load $(cat /proc/loadavg)" >> /home/sasa/workspace/savior_ws/results/cpp_port/tables/timing_offline_load.txt
cd /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad
for s in hall_t1_L3 aisles_t1_L3; do
  echo "$(date +%T) offline $s load=$(cut -d' ' -f1 /proc/loadavg)" >> /home/sasa/workspace/savior_ws/results/cpp_port/tables/timing_offline_load.txt
  GPU= NT=1 NAME=cppport_toff_$s /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/cppbuild/run.sh sys2 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/ws/src/savior/savior_perception_cpp/tools/equiv_offline.py --seq $s --threads 1 --out /home/sasa/workspace/savior_ws/results/cpp_port/timing_offline/$s.json > /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/cpp/logs/toff_$s.log 2>&1
  NAME=cppport_tyolo_s_$s /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/cppbuild/run.sh sys2 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/ws/src/savior/savior_perception_cpp/tools/equiv_yolo.py --seq $s --ultra --engine /home/sasa/workspace/savior_ws/models/warehouse/yolo26s-seg-warehouse.engine --cache /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentN/detcache --out /home/sasa/workspace/savior_ws/results/cpp_port/timing_offline/yolo_s672_$s.json > /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/cpp/logs/tyolo_s_$s.log 2>&1
  NAME=cppport_tyolo_n_$s /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/cppbuild/run.sh sys2 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/ws/src/savior/savior_perception_cpp/tools/equiv_yolo.py --seq $s --ultra --engine /home/sasa/workspace/savior_ws/frozen_edge/models/yolo26n-seg-warehouse-672.engine --cache /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge/detcache/n672 --out /home/sasa/workspace/savior_ws/results/cpp_port/timing_offline/yolo_n672_$s.json > /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/cpp/logs/tyolo_n_$s.log 2>&1
done
/home/sasa/workspace/savior_ws/results/cpp_port/scripts/cpp_run_timing.sh py_main_ctrl cpp_main_final cpp_main_composed
CPUS=0-3 TD=timing_cpus4 /home/sasa/workspace/savior_ws/results/cpp_port/scripts/cpp_run_timing.sh py_main_ctrl cpp_main_final
echo "$(date) timing done" >> /home/sasa/workspace/savior_ws/results/cpp_port/tables/timing_offline_load.txt
