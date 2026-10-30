#!/usr/bin/env bash
# run_m2b.sh <seq> <method> <domain> -> results/<DSN>/<seq>/<method>/run_XX (one isolated container, offsets in series)
# M2b held-out benchmark. All settings come from results/p7/final_config.yaml (frozen) + final_config_addendum.yaml via
# m2b_args.py. Same container / savior-run protocol as results/p7/scripts/run_method.sh. Rate 0.5 ONLY.
# env: OFFSETS (default: warehouse 0.0..1.8 s; VIODE the P5 late-start offsets of the env), START (1), DSN (m2b_heldout/runs)
# INSTALL_OVERRIDE (verification only, t1): run with another install.
# Held-out sequences are refused unless the addendum is frozen (md5 file present and matching).
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
WS=/home/sasa/workspace/savior_ws
H=$WS/results/m2b_heldout
P7=$WS/results/p7
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/m2b
RATE=${RATE:-0.5}
[[ $RATE == 0.5 ]] || { echo "rate must be 0.5"; exit 4; }
[[ -n "${INSTALL_OVERRIDE:-}" && $SEQ != *_t1_* ]] && { echo "INSTALL_OVERRIDE is t1 only"; exit 3; }
if [[ $SEQ != *_t1_* ]]; then
  [[ -f $P7/final_config_addendum.md5 ]] || { echo "refusing $SEQ: addendum not frozen"; exit 3; }
  (cd $P7 && md5sum -c --status final_config_addendum.md5) || { echo "refusing $SEQ: addendum md5 mismatch"; exit 3; }
fi
mapfile -t L < <(python3 $H/scripts/m2b_args.py $SEQ $METHOD)
INSTALL=${INSTALL_OVERRIDE:-${L[0]}}; LAUNCH=${L[1]}; CFG=${L[2]}; BAG=${L[3]}; OVSET=${L[5]}; TOPICS=${L[6]}; PSET=${L[7]}
ARGS=("${L[@]:8}")
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$PSET")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
if [[ -z "${OFFSETS:-}" ]]; then
  case $SEQ in
    parking_lot_*) OFFSETS="5.5 5.7 5.9 6.1 6.3 6.5 6.7 6.9 7.1 7.3" ;;
    city_day_*)    OFFSETS="4.1 4.3 4.5 4.7 4.9 5.1 5.3 5.5 5.7 5.9" ;;
    city_night_*)  OFFSETS="6.1 6.3 6.5 6.7 6.9 7.1 7.3 7.5 7.7 7.9" ;;
    *)             OFFSETS="0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8" ;;
  esac
fi
START=${START:-1}
DSN=${DSN:-m2b_heldout/runs}
RD=$WS/results/$DSN/$SEQ/$METHOD
mkdir -p $RD
printf '%s\n' "INSTALL=$INSTALL" "LAUNCH=$LAUNCH" "CFG=$CFG" "BAG=$BAG" "OVSET=$OVSET" "TOPICS=$TOPICS" "PSET=$PSET" "ARGS=${ARGS[*]:-}" "OFFSETS=$OFFSETS" "START=$START" > $RD/m2b_settings_$START.txt
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $INSTALL/setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f \$R/launch.log ]] && gzip -f \$R/launch.log; i=\$((i+1)); done"
NAME="m2b_$(echo ${METHOD}_${SEQ} | tr '+' '_')_${START}_$DOM"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "$INNER"
