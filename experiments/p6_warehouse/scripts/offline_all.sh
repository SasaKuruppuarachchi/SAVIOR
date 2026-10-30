#!/usr/bin/env bash
# offline_all.sh "seq[:stamps]"... : offline_eval_wh.py (all VARIANTS) per sequence -> offline/<seq>.yaml (+ _inst.jsonl, qual/ npz)
R=/home/sasa/workspace/savior_ws/results/p6_warehouse
for a in "$@"; do q=${a%%:*}; st=""; [[ $a == *:* ]] && st=${a#*:}
  python3 $R/scripts/offline_eval_wh.py --seq $q --out $R/offline/$q.yaml --inst-out $R/offline/${q}_inst.jsonl \
    ${st:+--save-stamps $st --save-dir $R/offline/qual} > $R/offline/$q.log 2>&1 || echo "fail $q"
done
