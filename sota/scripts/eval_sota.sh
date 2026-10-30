#!/usr/bin/env bash
# eval_sota.sh <method dir>... : savior-eval multi (full sequence) with posyaw (protocol), se3 and sim3 alignment ->
# <method dir>/eval_<align>/ ; runs in the savior image (no network). GT = data/<dataset>/gt/<seq>.txt, dataset and seq
# taken from the parent dir name <dataset>_<seq>.
set -uo pipefail
WS=${SAVIOR_WS:-/home/sasa/workspace/savior_ws}
D=$(cd "$(dirname "$0")" && pwd)
CMD=""; MNT=""
for d in "$@"; do
  d=$(cd "$d" && pwd); seq=$(basename "$(dirname "$d")"); ds=${seq%%_*}; seq=${seq#*_}; m=$(basename "$d")
  GT=$WS/data/$ds/gt/$seq.txt
  [[ $d == $WS/* ]] || MNT="$MNT -v $d:$d"
  [[ -f $GT ]] || { echo "no GT for $seq"; continue; }
  for a in ${ALIGNS:-posyaw se3 sim3}; do
    CMD="$CMD savior-eval multi --runs $d --gt $GT --label $m --align $a --out $d/eval_$a --no-plot > $d/eval_$a.log 2>&1 || echo 'eval fail $d $a';"
  done
  CMD="$CMD python3 -I $D/check_frames.py $GT $d/run_*/stamped_traj_estimate.txt > $d/check_frames.txt 2>&1;"
done
docker run --rm -i --network none --ipc private -v $WS:$WS $MNT -v $D:$D:ro -e HOME=/tmp -e MPLCONFIGDIR=/tmp -w /tmp savior:humble-cuda12.8 \
  bash -c "source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; $CMD"
