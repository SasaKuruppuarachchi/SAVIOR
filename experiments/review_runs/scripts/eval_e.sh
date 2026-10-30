#!/usr/bin/env bash
# eval_e.sh [method dir ...]: savior-eval multi (posyaw, full sequence, = P2/P3a/P7-D) + runstats for task-E runs (inside the image)
WS=/home/sasa/workspace/savior_ws; R=$WS/results/review_runs/runs/e
for d in ${@:-$R/*/*/}; do
  d=${d%/}; m=$(basename $d); seq=$(basename $(dirname $d)); ds=${seq%%_*}; raw=${seq#*_}
  gt=$WS/data/$ds/gt/$raw.txt; [[ -f $gt ]] || { echo "no gt $seq"; continue; }
  ls $d/run_*/stamped_traj_estimate.txt >/dev/null 2>&1 || continue
  savior-eval multi --runs $d --gt $gt --label $m --no-plot > $d/eval_multi.log 2>&1 || echo "eval fail $d"
  savior-eval runstats --runs $d --out $d/runstats.md > $d/runstats.log 2>&1 || echo "runstats fail $d"
done
