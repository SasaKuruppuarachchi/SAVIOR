#!/usr/bin/env bash
# run_sequence.sh <seq> <method>... : convert data/viode/ros2/<seq> to a temporary ROS 1 bag, run every method in its own
# isolated container (in parallel; RUNS / FROMSTART / ROOT / RATE as in run_method.sh), then DELETE the ROS 1 bag.
# env: BAGDIR (scratch dir for the temporary bag), FROMSTART_TOO=1 (also one bag-start run per method)
set -euo pipefail
SEQ=$1; shift
D=$(cd "$(dirname "$0")" && pwd)
BAGDIR=${BAGDIR:?set BAGDIR to a scratch directory for temporary ROS 1 bags}
BAG=$BAGDIR/$SEQ.bag
[[ -f $BAG ]] || $D/make_ros1_bag.sh $SEQ $BAG
trap 'rm -f "$BAG"; echo "deleted $BAG"' EXIT
pids=()
for m in "$@"; do
  $D/run_method.sh $SEQ $m $BAG & pids+=($!)
  if [[ -n "${FROMSTART_TOO:-}" ]]; then FROMSTART=1 $D/run_method.sh $SEQ $m $BAG & pids+=($!); fi
done
rc=0; for p in "${pids[@]}"; do wait $p || rc=1; done
exit $rc
