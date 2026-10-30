#!/usr/bin/env bash
# rw_sota.sh <seq> <method> <domain-unused> : VINS-Fusion / DynaVINS (src/savior/sota run_one.sh, SOTA_DATASET=monado config)
# on the 54 Hz ROS 1 bag data/monado/ros1/<seq>.bag -> results/real_world/runs/<seq>/<method>/run_XX, offsets in series in ONE
# savior-sota:noetic container named rw_sota_* (counts against the rw_ container cap). Rate 0.25 (FREEZE_AMENDMENT 2).
# method ros1conv: build the ROS 1 bag (savior image). env: OFFSETS (0.0..1.8), START (1)
set -euo pipefail
SEQ=$1; METHOD=$2
WS=/home/sasa/workspace/savior_ws; H=$WS/results/real_world; SOTA=$WS/src/savior/sota
declare -A ZIP=([MIO13]=MIO13_moving_person [MIO15]=MIO15_moving_person_props [MIO16]=MIO16_moving_screens_person_props [MIO07]=MIO07_mapping_easy)
B=$WS/data/monado/ros1; BAG=$B/$SEQ.bag
if [[ $METHOD == ros1conv ]]; then
  mkdir -p $B; [[ -f $BAG.done ]] && exit 0; rm -f $BAG
  docker run --rm --name rw_ros1conv_$SEQ --network none -u $(id -u):$(id -g) -v $WS:$WS savior:humble-cuda12.8 \
    python3 -I $H/scripts/rw_make_ros1.py --zip $WS/data/monado/raw/${ZIP[$SEQ]}.zip --dst $BAG > $B/$SEQ.conv.log 2>&1
  grep -q "counts OK" $B/$SEQ.conv.log && touch $BAG.done; exit 0
fi
case $METHOD in vins_fusion|dynavins) ;; *) echo "unknown method $METHOD"; exit 2 ;; esac
until [[ -f $BAG.done ]]; do sleep 20; done
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8}; START=${START:-1}; RATE=${RATE:-0.25}   # FREEZE_AMENDMENT 2 (A5): rate 0.25 (was 0.5)
OUT=$H/runs/$SEQ/$METHOD; mkdir -p $OUT
PAIRS=""; i=$START; for o in $OFFSETS; do PAIRS="$PAIRS $i:$o"; i=$((i+1)); done
INNER="for p in $PAIRS; do i=\${p%%:*}; off=\${p#*:}; R=$OUT/run_\$(printf %02d \$i); rm -rf \$R; mkdir -p \$R; \
  bash $SOTA/scripts/run_one.sh $METHOD $BAG \$R \$off $RATE > \$R/run.log 2>&1 || echo \"run \$i rc=\$?\"; \
  grep -E '^(status|n_poses|wall_time_s):' \$R/run_info.yaml | tr '\n' ' '; echo \" [$SEQ $METHOD run_\$i off \$off]\"; done"
SOTA_SEQ=$SEQ SOTA_DATASET=monado exec $SOTA/scripts/drun_sota.sh "rw_sota_${METHOD}_${SEQ}_${START}" "$B" bash -c "$INNER"
