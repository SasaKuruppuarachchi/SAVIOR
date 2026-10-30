#!/usr/bin/env bash
# run_heldout_v2.sh <seq> <method> <domain> -> results/backend_v2/heldout/runs/<seq>/<method>/run_XX
# HELD-OUT runner of the back-end v2 benchmark (warehouse t2 + VIODE). DO NOT RUN before the author-facing freeze: refuses unless
#   CONFIRM_HELDOUT=yes, results/backend_v2/backend_config.md5 verifies, and the frozen final_config / addendum md5 verify
#   (bv2_args.py asserts the latter and every v2 file md5).
# Same container / savior-run protocol as results/m2b_heldout/scripts/run_m2b.sh (rate 0.5, VIODE P5 late-start offsets).
# env: OFFSETS, START (1), BACKEND (v2), BACKEND_VIODE (default v2 = identical rule; v1 = frozen VIODE estimator), DSN.
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
WS=/home/sasa/workspace/savior_ws
H=$WS/results/backend_v2
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/bv2
[[ ${CONFIRM_HELDOUT:-} == yes ]] || { echo "refusing $SEQ: set CONFIRM_HELDOUT=yes only after the author-facing freeze"; exit 3; }
(cd $H && md5sum -c --status backend_config.md5) || { echo "refusing: backend_config.yaml md5 mismatch / no md5 file"; exit 3; }
(cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) || { echo "refusing: frozen md5"; exit 3; }
[[ $SEQ == *_t2_* || $SEQ == parking_lot_* || $SEQ == city_day_* || $SEQ == city_night_* ]] || { echo "held-out runner: t2 / VIODE only"; exit 3; }
RATE=0.5
BACKEND=${BACKEND:-v2}
export BACKEND_VIODE=${BACKEND_VIODE:-v2}
mapfile -t L < <(python3 $H/scripts/bv2_args.py $SEQ $METHOD $BACKEND)
[[ ${#L[@]} -ge 8 ]] || { echo "bv2_args failed"; exit 2; }
INSTALL=${L[0]}; LAUNCH=${L[1]}; CFG=${L[2]}; BAG=${L[3]}; OVSET=${L[5]}; TOPICS=${L[6]}; PSET=${L[7]}
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
DSN=${DSN:-backend_v2/heldout/runs}
RD=$WS/results/$DSN/$SEQ/$METHOD
mkdir -p $RD
printf '%s\n' "BACKEND=$BACKEND" "BACKEND_VIODE=$BACKEND_VIODE" "INSTALL=$INSTALL" "LAUNCH=$LAUNCH" "CFG=$CFG" "BAG=$BAG" "OVSET=$OVSET" \
  "TOPICS=$TOPICS" "PSET=$PSET" "ARGS=${ARGS[*]:-}" "OFFSETS=$OFFSETS" "START=$START" > $RD/bv2_settings_$START.txt
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $INSTALL/setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f \$R/launch.log ]] && gzip -f \$R/launch.log; i=\$((i+1)); done"
NAME="bv2h_$(echo ${METHOD}_${SEQ} | tr '+' '_')_${START}_$DOM"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "$INNER"
