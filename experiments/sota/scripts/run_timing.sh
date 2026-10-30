#!/usr/bin/env bash
# run_timing.sh : M3b per-frame timing, ONE savior-sota container at a time (4 CPUs, as the benchmark), offset index 1,
# rate 0.5 -> results/sota/timing/<dataset>_<seq>/<method>/run_01 (timing.csv). Logs host load / other containers.
# VIODE parking_lot_high + city_day_high: all 3 methods; warehouse hall_t2_L3: VINS-Fusion + DynaVINS (ORB-SLAM3 never
# initializes on the warehouse with upstream defaults, so its TrackStereo time there is not meaningful).
set -uo pipefail
WS=/home/sasa/workspace/savior_ws; S=$WS/src/savior/sota/scripts
SP=${BAGDIR:?}; export ROOT=$WS/results/sota/timing RUNS=1
mkdir -p $ROOT
run() {  # dataset seq methods...
  local ds=$1 seq=$2; shift 2; local bag=$SP/timing_$seq.bag
  DATASET=$ds $S/make_ros1_bag.sh $seq $bag > $ROOT/conv_$seq.log 2>&1 || { echo "conv fail $seq"; return; }
  for m in "$@"; do
    { date +%T; uptime; docker ps --format '{{.Names}}' | wc -l; } > $ROOT/load_${ds}_${seq}_$m.txt
    DATASET=$ds $S/run_method.sh $seq $m $bag
    { date +%T; uptime; docker ps --format '{{.Names}}' | wc -l; } >> $ROOT/load_${ds}_${seq}_$m.txt
  done
  rm -f $bag
}
run viode parking_lot_high vins_fusion dynavins orbslam3
run viode city_day_high vins_fusion dynavins orbslam3
run warehouse hall_t2_L3 vins_fusion dynavins
echo TIMING_DONE
