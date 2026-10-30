#!/usr/bin/env bash
# eval_all.sh [start_time] [dir glob]: savior-eval multi (full + common window from start_time) + runstats for every P3a method dir
WS=/home/sasa/workspace/savior_ws; P3=$WS/results/p3a; ST=${1:-45}
for d in ${2:-$P3/uhumans2_office_s1_*/*/}; do
  m=$(basename $d); s=$(basename $(dirname $d)); seq=${s#uhumans2_}
  ls $d/run_0*/stamped_traj_estimate.txt >/dev/null 2>&1 || continue
  savior-eval multi --runs $d --gt $WS/data/uhumans2/gt/$seq.txt --label $m --plot-format png > $d/eval_multi.log 2>&1 || echo "eval fail $d"
  savior-eval multi --runs $d --gt $WS/data/uhumans2/gt/$seq.txt --label $m --out $d/eval_w45 --start-time $ST --no-plot > $d/eval_w45.log 2>&1 || echo "eval_w45 fail $d"
  savior-eval multi --runs $d --gt $WS/data/uhumans2/gt/$seq.txt --label $m --out $d/eval_mid --start-time $ST --end-time 480 --no-plot > $d/eval_mid.log 2>&1 || echo "eval_mid fail $d"
  savior-eval runstats --runs $d --out $d/runstats.md > $d/runstats.log 2>&1 || echo "runstats fail $d"
done
