#!/usr/bin/env bash
# eval_all.sh [dir glob]: savior-eval multi (posyaw, full sequence) + runstats for every P6 method dir (inside the image)
WS=/home/sasa/workspace/savior_ws; P=$WS/results/p6_warehouse
for d in ${1:-$P/*_t1_L*/*/}; do
  d=${d%/}; m=$(basename $d); seq=$(basename $(dirname $d))
  [[ -f $WS/data/warehouse/gt/$seq.txt ]] || continue
  ls $d/run_*/stamped_traj_estimate.txt >/dev/null 2>&1 || continue
  savior-eval multi --runs $d --gt $WS/data/warehouse/gt/$seq.txt --label $m --no-plot > $d/eval_multi.log 2>&1 || echo "eval fail $d"
  savior-eval runstats --runs $d --out $d/runstats.md > $d/runstats.log 2>&1 || echo "runstats fail $d"
done
