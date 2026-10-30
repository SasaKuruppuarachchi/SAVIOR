#!/usr/bin/env bash
# cpp_eval_all.sh [method ...]: savior-eval multi (posyaw, full sequence) for C++ port method dirs (inside the image)
WS=/home/sasa/workspace/savior_ws; R=$WS/results/cpp_port/runs
for m in "$@"; do for d in $R/*_t1_L*/$m; do
  [[ -d $d ]] || continue; seq=$(basename $(dirname $d))
  ls $d/run_*/stamped_traj_estimate.txt >/dev/null 2>&1 || continue
  savior-eval multi --runs $d --gt $WS/data/warehouse/gt/$seq.txt --label $m --no-plot > $d/eval_multi.log 2>&1 || echo "eval fail $d"
done; done
