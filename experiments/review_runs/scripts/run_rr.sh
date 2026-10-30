#!/usr/bin/env bash
# run_rr.sh <seq> <variant> <domain> -> results/<DSN>/<seq>/<variant>/run_XX  (one isolated container, offsets in series)
# Review runs. Identical container / savior-run protocol to results/backend_v2/scripts/run_bv2.sh and run_heldout_v2.sh
# (rate 0.5, mask_policy wait, timeout 30 s, feature_stats auto, VIODE P5 late-start offsets); settings from rr_args.py
# (= bv2_args.py of the frozen base method + the variant delta). Held-out sequences need CONFIRM_HELDOUT=yes and the
# read-only FREEZE.yaml (checked in rr_args.py); also re-checks the frozen md5 files.
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
WS=/home/sasa/workspace/savior_ws
H=$WS/results/backend_v2
RR=$WS/results/review_runs
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/rr
(cd $H && md5sum -c --status backend_config.md5) || { echo "refusing: backend_config.yaml md5 mismatch"; exit 3; }
(cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) || { echo "refusing: frozen md5"; exit 3; }
if [[ $SEQ != *_t1_* ]]; then
  [[ ${CONFIRM_HELDOUT:-} == yes ]] || { echo "refusing $SEQ: held-out needs CONFIRM_HELDOUT=yes"; exit 3; }
  (cd $RR && md5sum -c --status FREEZE.md5) || { echo "refusing: FREEZE.yaml md5"; exit 3; }
  DSN=${DSN:-review_runs/runs/heldout}
else
  DSN=${DSN:-review_runs/runs/t1}
fi
RATE=0.5
export BACKEND_VIODE=v2
mapfile -t L < <(python3 $RR/scripts/rr_args.py $SEQ $METHOD)
[[ ${#L[@]} -ge 8 ]] || { echo "rr_args failed"; exit 2; }
INSTALL=${L[0]}; LAUNCH=${L[1]}; CFG=${L[2]}; BAG=${L[3]}; OVSET=${L[5]}; TOPICS=${L[6]}; PSET=${L[7]}
ARGS=("${L[@]:8}")
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET")
# AMENDMENT 1 (2026-10-27, FREEZE_AMENDMENT.txt): an empty TOPICS (task E: dataset preset) is not passed (ros2 launch rejects
# 'topics:='); E bags are symlinks into /home/hdd/sasa/archive/savior, mounted read-only. No variant setting changes.
[[ -n "${TOPICS// }" ]] && LA+=(--launch-arg "topics:=$TOPICS")
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
RD=$WS/results/$DSN/$SEQ/$METHOD
mkdir -p $RD
printf '%s\n' "VARIANT=$METHOD" "INSTALL=$INSTALL" "LAUNCH=$LAUNCH" "CFG=$CFG" "BAG=$BAG" "OVSET=$OVSET" \
  "TOPICS=$TOPICS" "PSET=$PSET" "ARGS=${ARGS[*]:-}" "OFFSETS=$OFFSETS" "START=$START" > $RD/rr_settings_$START.txt
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $INSTALL/setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f \$R/launch.log ]] && gzip -f \$R/launch.log; i=\$((i+1)); done"
NAME="rr_$(echo ${METHOD}_${SEQ} | tr '+' '_')_${START}_$DOM"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -v /home/hdd/sasa/archive/savior:/home/hdd/sasa/archive/savior:ro -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "$INNER"
