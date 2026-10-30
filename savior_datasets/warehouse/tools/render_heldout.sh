#!/usr/bin/env bash
# Render + convert the HELD-OUT test split (scenes/<scene>_t2.py ...), one Isaac process at a time.
#   tools/render_heldout.sh <scene_module>:<level> ...      e.g. aisles_t2:0 aisles_t2:3 dock_t2:2
# Raw -> data/warehouse/raw/<seq>; bag with the right-camera segmentation (--seg-right) ->
# data/warehouse/ros2_stereoseg/<seq>; GT -> data/warehouse/gt/<seq>.txt. No plain ros2/<seq> bag is written for the
# held-out split (the stereoseg bag holds every topic of it, byte-identical).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS="$(cd "$HERE/../../../.." && pwd)"
ISAAC_PY="${ISAAC_PY:-$HOME/isaacsim/python.sh}"
LOGS="$WS/data/warehouse/logs"; mkdir -p "$LOGS"
[[ $# -gt 0 ]] || { echo "usage: $0 <scene_module>:<level> ..."; exit 1; }
for j in "$@"; do
  mod=${j%%:*}; level=${j##*:}
  seq=$(cd "$HERE" && "$ISAAC_PY" -c "import importlib; m = importlib.import_module('scenes.$mod'); print(f'{m.NAME}_{m.TRAJ}_L$level')" 2>/dev/null | tail -1)
  echo "[render_heldout] $(date +%T) $seq ($mod level $level)"
  rm -rf "$WS/data/warehouse/raw/$seq"
  "$ISAAC_PY" "$HERE/isaac/render_sequence.py" --scene "$mod" --level "$level" > "$LOGS/render_$seq.log" 2>&1
  grep " done:" "$LOGS/render_$seq.log" || { echo "[render_heldout] $seq FAILED"; continue; }
  (cd "$WS" && src/savior/docker/exec.sh python3 -I src/savior/savior_datasets/warehouse/tools/to_ros2.py \
      --raw "data/warehouse/raw/$seq" --out "data/warehouse/ros2_stereoseg/$seq" --seg-right --force) \
      > "$LOGS/to_ros2_$seq.log" 2>&1 && tail -1 "$LOGS/to_ros2_$seq.log"
done
echo "[render_heldout] $(date +%T) finished"
