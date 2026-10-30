#!/usr/bin/env bash
# Render + convert the CONFIRMATORY split t3 (scenes/procedural.py, results/t3_confirmatory/DESIGN.yaml), one Isaac
# process at a time; the ROS 2 conversion of sequence k (Docker) overlaps with the rendering of k+1.
#   tools/render_t3.sh <traj_id>:<level> ...        e.g. fw01:0 fw01:3 wx04:2
# Storage (NVMe is small): raw and bags go to $T3_ROOT (default: the HDD archive), with symlinks from the workspace
#   raw  -> $T3_ROOT/raw/<seq>              symlink data/warehouse/raw/<seq>
#   bag  -> $T3_ROOT/ros2_stereoseg/<seq>    symlink data/warehouse/ros2_stereoseg/<seq>   (--seg-right, like t2)
#   GT   -> data/warehouse/gt/<seq>.txt (small, NVMe)
# Logs: $T3_ROOT/logs/. A sequence whose raw dir already has meta.json + a converted bag is skipped (FORCE=1 redoes it).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS="$(cd "$HERE/../../../.." && pwd)"
ISAAC_PY="${ISAAC_PY:-/home/sasa/isaacsim/python.sh}"
T3_ROOT="${T3_ROOT:-/home/hdd/sasa/archive/savior/workspace/data/warehouse/t3}"
LOGS="$T3_ROOT/logs"; mkdir -p "$LOGS" "$T3_ROOT/raw" "$T3_ROOT/ros2_stereoseg" "$WS/data/warehouse/gt"
[[ $# -gt 0 ]] || { echo "usage: $0 <traj_id>:<level> ..."; exit 1; }
convert() {   # <seq>  (Docker; HDD mounted)
  local seq=$1
  docker run --rm --init -i --name "t3conv_$seq" --network none -u "$(id -u):$(id -g)" -e HOME=/tmp \
    -v "$WS:$WS" -v "$T3_ROOT:$T3_ROOT" -w "$WS" savior:humble-cuda12.8 \
    python3 -I src/savior/savior_datasets/warehouse/tools/to_ros2.py --raw "$T3_ROOT/raw/$seq" \
      --out "$T3_ROOT/ros2_stereoseg/$seq" --gt "$WS/data/warehouse/gt/$seq.txt" --seg-right --force \
    > "$LOGS/to_ros2_$seq.log" 2>&1
  if tail -1 "$LOGS/to_ros2_$seq.log" | grep -q "stereo frames"; then
    ln -sfn "$T3_ROOT/ros2_stereoseg/$seq" "$WS/data/warehouse/ros2_stereoseg/$seq"
    echo "[render_t3] $(date +%T) $seq converted: $(tail -1 "$LOGS/to_ros2_$seq.log")"
  else
    echo "[render_t3] $(date +%T) $seq CONVERSION FAILED (see $LOGS/to_ros2_$seq.log)"
  fi
}
CPID=""
for j in "$@"; do
  id=${j%%:*}; level=${j##*:}; seq="${id}_t3_L${level}"
  if [[ -z "${FORCE:-}" && -f "$T3_ROOT/raw/$seq/meta.json" && -f "$T3_ROOT/ros2_stereoseg/$seq/metadata.yaml" ]]; then
    echo "[render_t3] $seq exists, skipped"; continue
  fi
  echo "[render_t3] $(date +%T) render $seq"
  rm -rf "$T3_ROOT/raw/$seq"
  (cd "$HERE" && "$ISAAC_PY" isaac/render_sequence.py --scene "procedural:$id" --level "$level" --out "$T3_ROOT/raw/$seq") \
    > "$LOGS/render_$seq.log" 2>&1
  grep " done:" "$LOGS/render_$seq.log" || { echo "[render_t3] $seq RENDER FAILED"; continue; }
  ln -sfn "$T3_ROOT/raw/$seq" "$WS/data/warehouse/raw/$seq"
  [[ -n "$CPID" ]] && wait "$CPID"
  convert "$seq" & CPID=$!
done
[[ -n "$CPID" ]] && wait "$CPID"
echo "[render_t3] $(date +%T) finished"
