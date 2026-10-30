#!/usr/bin/env bash
# Render + convert SAVIOR-Warehouse sequences one after the other (one Isaac process at a time).
#   tools/render_all.sh [scene:level ...]      default: all 2 scenes x 4 levels
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS="$(cd "$HERE/../../../.." && pwd)"
ISAAC_PY="${ISAAC_PY:-$HOME/isaacsim/python.sh}"
LOGS="$WS/data/warehouse/logs"; mkdir -p "$LOGS"
JOBS=("$@"); [[ ${#JOBS[@]} -eq 0 ]] && JOBS=(aisles:0 aisles:1 aisles:2 aisles:3 hall:0 hall:1 hall:2 hall:3)
for j in "${JOBS[@]}"; do
  scene=${j%%:*}; level=${j##*:}; seq="${scene}_t1_L${level}"
  echo "[render_all] $(date +%T) $seq"
  rm -rf "$WS/data/warehouse/raw/$seq"
  "$ISAAC_PY" "$HERE/isaac/render_sequence.py" --scene "$scene" --level "$level" > "$LOGS/render_$seq.log" 2>&1
  grep " done:" "$LOGS/render_$seq.log" || { echo "[render_all] $seq FAILED"; continue; }
  (cd "$WS" && src/savior/docker/exec.sh python3 -I src/savior/savior_datasets/warehouse/tools/to_ros2.py \
      --raw "data/warehouse/raw/$seq" --force) > "$LOGS/to_ros2_$seq.log" 2>&1 && tail -1 "$LOGS/to_ros2_$seq.log"
done
echo "[render_all] $(date +%T) finished"
