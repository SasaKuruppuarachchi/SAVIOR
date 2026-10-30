#!/usr/bin/env bash
# diag_all.sh: diag_p6.py for every diag_* run with a diag_updates.csv (inside the image)
P=/home/sasa/workspace/savior_ws/results/p6_warehouse
for r in $P/*_t1_L*/diag_*/run_*; do
  seq=$(basename $(dirname $(dirname $r)))
  [[ -f $r/diag_updates.csv ]] || continue
  [[ -f $r/diag_p6.yaml && $r/diag_p6.yaml -nt $r/diag_updates.csv ]] || python3 $P/scripts/diag_p6.py --diag $r/diag_updates.csv --seq $seq --out $r/diag_p6.yaml > /dev/null || echo "fail $r"
done
