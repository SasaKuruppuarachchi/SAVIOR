#!/usr/bin/env bash
# dmrun.sh <t1|t2|viode> <seq> <tag> [KEY=VAL ...] : one isolated savior-sota:noetic-mask-dyna container
# (src/savior/sota/scripts/run_method_dm.sh), DynaVINS, 10 offsets in series -> <ROOT>/<dataset>_<seq>/<tag>/run_XX.
# Defaults: METHOD dynavins, RUNS 1..10, RATE 0.5, ROOT results/dynavins_masks/runs (t1) | runs_<t2|viode> (held-out).
# Held-out (t2 / viode) only with DM_HELDOUT_GO=1 (set by run_heldout.sh after the freeze check).
set -euo pipefail
DSET=$1; SEQ=$2; TAG=$3; shift 3
WS=/home/sasa/workspace/savior_ws; R=$WS/results/dynavins_masks
S=${DM_SCRATCH:-/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/dm}
case $DSET in
  t1) [[ $SEQ == *_t1_* ]] || { echo "refusing $SEQ for t1"; exit 3; }
      export DATASET=warehouse OFFSETS_FILE=$WS/results/vins_savior/scripts/t1_offsets.txt ROOT=$R/runs ;;
  t2) [[ ${DM_HELDOUT_GO:-} == 1 && $SEQ == *_t2_* ]] || { echo "held-out only via run_heldout.sh"; exit 3; }
      export DATASET=warehouse OFFSETS_FILE=$WS/src/savior/sota/scripts/warehouse_offsets.txt ROOT=$R/runs_t2 ;;
  viode) [[ ${DM_HELDOUT_GO:-} == 1 ]] || { echo "held-out only via run_heldout.sh"; exit 3; }
      export DATASET=viode OFFSETS_FILE=$WS/src/savior/sota/scripts/viode_offsets.txt ROOT=$R/runs_viode ;;
  *) echo "unknown dataset $DSET"; exit 2 ;;
esac
export METHOD=dynavins SOTA_IMAGE=savior-sota:noetic-mask-dyna RUNS="1 2 3 4 5 6 7 8 9 10"
for kv in "$@"; do export "$kv"; done
RUNS=${RUNS//,/ }
export MDIR_NAME=$TAG RATE=0.5
exec $WS/src/savior/sota/scripts/run_method_dm.sh $SEQ $METHOD $S/bags/$SEQ.bag
