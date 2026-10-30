#!/usr/bin/env bash
# vrun.sh <seq> <tag> [KEY=VAL ...] : one isolated savior-sota container (src/savior/sota/scripts/run_method.sh), t1 only.
# method dir <ROOT>/warehouse_<seq>/<tag>/run_XX. Defaults: image savior-sota:noetic-mask, method vins_fusion, RUNS 1..10,
# ROOT results/vins_savior/runs. KEY=VAL are exported (METHOD, RUNS, ROOT, SOTA_IMAGE, SOTA_MASK_DIR, SOTA_DETERMINISTIC ...)
set -euo pipefail
SEQ=$1; TAG=$2; shift 2
[[ $SEQ == *_t1_* ]] || { echo "refusing $SEQ (t1 only)"; exit 3; }
WS=/home/sasa/workspace/savior_ws; V=$WS/results/vins_savior
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/vs
export METHOD=vins_fusion SOTA_IMAGE=savior-sota:noetic-mask ROOT=$V/runs RUNS="1 2 3 4 5 6 7 8 9 10"
for kv in "$@"; do export "$kv"; done
RUNS=${RUNS//,/ }
export DATASET=warehouse OFFSETS_FILE=$V/scripts/t1_offsets.txt MDIR_NAME=$TAG RATE=0.5
exec $WS/src/savior/sota/scripts/run_method.sh $SEQ $METHOD $S/bags/$SEQ.bag
