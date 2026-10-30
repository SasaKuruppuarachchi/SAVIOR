#!/usr/bin/env bash
# online_record.sh <seq> <method> <run index> <domain> : re-run ONE frozen online OpenVINS+SAVIOR run (exactly as
# results/m2b_heldout/scripts/run_m2b.sh, settings from m2b_args.py = frozen yamls) and record the published masks
# (/savior/mask/left|right, ros2 bag) -> results/vins_savior/validation/online/<seq>/<method>/run_XX (t1 only).
set -euo pipefail
SEQ=$1; METHOD=$2; IDX=$3; DOM=$4
[[ $SEQ == *_t1_* ]] || { echo "t1 only"; exit 3; }
WS=/home/sasa/workspace/savior_ws
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/vs
RATE=0.5
mapfile -t L < <(python3 $WS/results/m2b_heldout/scripts/m2b_args.py $SEQ $METHOD)
INSTALL=${L[0]}; LAUNCH=${L[1]}; CFG=${L[2]}; BAG=${L[3]}; OVSET=${L[5]}; TOPICS=${L[6]}; PSET=${L[7]}
ARGS=("${L[@]:8}")
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
[[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$PSET")
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
OFFS=(0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8); off=${OFFS[$((IDX-1))]}
DSN=vins_savior/validation/online
RD=$WS/results/$DSN/$SEQ/$METHOD; R=$RD/run_$(printf %02d $IDX)
rm -rf $R; mkdir -p $R
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $INSTALL/setup.bash; \
  ros2 bag record -o $R/masks_bag /savior/mask/left /savior/mask/right > $R/record.log 2>&1 & REC=\$!; sleep 3; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index $IDX --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=$off $(printf '%q ' "${LA[@]}") || echo run failed; \
  sleep 3; kill -INT \$REC; wait \$REC; [[ -f $R/savior_stats.jsonl ]] && gzip -f $R/savior_stats.jsonl; [[ -f $R/launch.log ]] && gzip -f $R/launch.log; true"
exec docker run --rm --init -i --name "vs_online_${METHOD}_${SEQ}_$IDX" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "$INNER"
