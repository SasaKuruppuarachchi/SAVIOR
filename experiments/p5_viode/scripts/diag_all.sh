#!/usr/bin/env bash
# diag_all.sh: diag_p5.py (dyn / static / all vehicles) for every diag_openvins run (inside the image)
P=/home/sasa/workspace/savior_ws/results/p5_viode; G=/home/sasa/workspace/savior_ws/data/viode/gt/masks
for r in $P/*/diag_openvins/run_*; do
  seq=$(basename $(dirname $(dirname $r)))
  [[ -f $r/diag_updates.csv ]] || continue
  for k in dyn static all; do
    [[ -f $r/diag_$k.yaml ]] || python3 $P/scripts/diag_p5.py --diag $r/diag_updates.csv --masks $G/$seq.npz --klass $k --out $r/diag_$k.yaml > /dev/null || echo "fail $r $k"
  done
done
