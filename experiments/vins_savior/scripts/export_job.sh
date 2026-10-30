#!/usr/bin/env bash
# export_job.sh <seq> <method> : one container, 10 offsets -> results/vins_savior/masks/<seq>/<method>/off_X.Y,
# then per-offset comparison of the /savior/stats records with the online OpenVINS run (validation).
set -euo pipefail
SEQ=$1; M=$2
[[ $SEQ == *_t1_* ]] || { echo "refusing $SEQ (t1 only)"; exit 3; }
WS=/home/sasa/workspace/savior_ws; V=$WS/results/vins_savior; R=$WS/results
OFFS="0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8"
case $M in
  sens_fix1|oracle_class_ext) REF=$R/p7/$SEQ/$M; INST=$WS/install ;;
  yolo_naive|oracle_moving_ext) REF=$R/p6_warehouse/$SEQ/$M; INST=$WS/install ;;
  savior_edge) REF=$R/edge_study/runs/$SEQ/e_c_n672_L250dfronly; INST=$WS/frozen_edge/install ;;
esac
LOG=$(ls $REF/run_01/launch.log* | head -1)
[[ $M == savior_edge ]] && LOG=$(ls $R/m2b_heldout/verify/hall_t1_L3/savior_edge/run_03/launch.log* 2>/dev/null | head -1)
INNER="python3 $WS/src/savior/sota/mask_export/export_masks.py --seq $SEQ --method $M --offsets $OFFS --out $V/masks --refuse _t2_,_t3_ ${LOG:+--check-log $LOG} 2>&1 | grep -E 'PARAM|frames, md5|Error|error' ; \
 i=1; for o in $OFFS; do r=\$(printf %02d \$i); echo -n \"$SEQ $M off_\$o run_\$r \"; python3 $V/scripts/cmp_stats.py $V/masks/$SEQ/$M/off_\$o/stats.jsonl.gz $REF/run_\$r/savior_stats.jsonl.gz; i=\$((i+1)); done"
$V/scripts/srun.sh "exp_${M}_${SEQ}" $INST bash -c "$INNER"
