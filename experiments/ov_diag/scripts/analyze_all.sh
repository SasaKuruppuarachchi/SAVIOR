#!/usr/bin/env bash
# analyze_all.sh : timeline.py over every finished run (ov_diag runs + VINS-Fusion t1 runs), then aggregate.py
WS=/home/sasa/workspace/savior_ws; D=$WS/results/ov_diag
RUNS=$(ls -d $D/runs/*/*/run_* $D/vins/*/vins_fusion/run_* 2>/dev/null | while read r; do [[ -f $r/run_info.yaml ]] && echo $r; done)
GPU= NT=8 bash $WS/results/p7/scripts/gpy.sh $D/scripts/timeline.py $D/analysis/runs.json $RUNS
GPU= bash $WS/results/p7/scripts/gpy.sh $D/scripts/aggregate.py $D/analysis/runs.json base
