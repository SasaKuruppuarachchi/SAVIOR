#!/usr/bin/env bash
# hvrun.sh <dataset t2|viode> <seq> <tag> [KEY=VAL ...] : held-out twin of ../vrun.sh (one savior-sota container,
# run_method.sh, 10 offsets in series). Only called by run_heldout.sh (which checks the freeze).
set -euo pipefail
DSET=$1; SEQ=$2; TAG=$3; shift 3
[[ ${VS_HELDOUT_GO:-} == 1 ]] || { echo "hvrun.sh: only via run_heldout.sh"; exit 3; }
WS=/home/sasa/workspace/savior_ws; V=$WS/results/vins_savior; H=$V/heldout
S=${VS_SCRATCH:?}
export METHOD=vins_fusion SOTA_IMAGE=savior-sota:noetic-mask ROOT=$H/runs_$DSET RUNS="1 2 3 4 5 6 7 8 9 10"
for kv in "$@"; do export "$kv"; done
if [[ $DSET == viode ]]; then export DATASET=viode OFFSETS_FILE=$WS/src/savior/sota/scripts/viode_offsets.txt
else export DATASET=warehouse OFFSETS_FILE=$WS/src/savior/sota/scripts/warehouse_offsets.txt; fi
export MDIR_NAME=$TAG RATE=0.5
exec $WS/src/savior/sota/scripts/run_method.sh $SEQ $METHOD $S/bags/$SEQ.bag
