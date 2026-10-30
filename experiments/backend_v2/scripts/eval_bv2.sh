#!/usr/bin/env bash
# eval_bv2.sh [method dir ...]: savior-eval multi (posyaw, full sequence) + runstats per method dir (run INSIDE the image,
# e.g. scripts/bpy.sh scripts/eval_bv2.sh). = results/m2b_heldout/scripts/eval_m2b.sh with ROOT default results/backend_v2/runs.
WS=/home/sasa/workspace/savior_ws; R=${ROOT:-$WS/results/backend_v2/runs}
for d in ${@:-$R/*/*/}; do
  d=${d%/}; m=$(basename $d); seq=$(basename $(dirname $d))
  gt=$WS/data/warehouse/gt/$seq.txt; [[ -f $gt ]] || gt=$WS/data/viode/gt/$seq.txt
  [[ -f $gt ]] || { echo "no gt $seq"; continue; }
  ls $d/run_*/stamped_traj_estimate.txt >/dev/null 2>&1 || continue
  savior-eval multi --runs $d --gt $gt --label $m --no-plot > $d/eval_multi.log 2>&1 || echo "eval fail $d"
  savior-eval runstats --runs $d --out $d/runstats.md > $d/runstats.log 2>&1 || echo "runstats fail $d"
done
