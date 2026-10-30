#!/usr/bin/env bash
# finish_all.sh : after the run queues: posyaw evaluation (one container per sequence, in parallel), analysis, figures, control
set -uo pipefail
WS=/home/sasa/workspace/savior_ws; V=$WS/results/vins_savior
for s in aisles_t1_L0 aisles_t1_L1 aisles_t1_L2 aisles_t1_L3 hall_t1_L0 hall_t1_L1 hall_t1_L2 hall_t1_L3; do
  ds=(); for d in $V/runs/warehouse_$s/*/; do [[ -f $d/eval_posyaw/eval_summary.yaml && $d/eval_posyaw/eval_summary.yaml -nt $d/run_10/stamped_traj_estimate.txt ]] || ds+=($d); done
  [[ ${#ds[@]} -gt 0 ]] && ALIGNS=posyaw $WS/src/savior/sota/scripts/eval_sota.sh "${ds[@]}" > /dev/null 2>&1 &
done; wait
for met in ate rpe; do docker run --rm --network none -v $WS:$WS -e MPLCONFIGDIR=/tmp savior:humble-cuda12.8 python3 $V/scripts/vs_analyze.py --metric $met > /dev/null; done
docker run --rm --network none -v $WS:$WS savior:humble-cuda12.8 python3 $V/scripts/vs_control.py runs tables t1 > /dev/null
docker run --rm --network none -v $WS:$WS -e MPLCONFIGDIR=/tmp savior:humble-cuda12.8 python3 $V/scripts/vs_figs.py > $V/tables/figs.log 2>&1
echo finished
