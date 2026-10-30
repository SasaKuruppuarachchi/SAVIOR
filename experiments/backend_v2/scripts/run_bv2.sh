#!/usr/bin/env bash
# run_bv2.sh <seq> <method> <domain> -> results/<DSN>/<seq>/<method>/run_XX (one isolated container, offsets in series)
# Back-end v2 t1 validation. Settings from bv2_args.py (frozen final_config + addendum through m2b_args.py; only the CFG
# changes to results/backend_v2/config/warehouse). Same container / savior-run protocol as results/m2b_heldout/scripts/run_m2b.sh.
# env: BACKEND (v2 | v1, default v2), OFFSETS (default 0.0..1.8 s), START (1), DSN (backend_v2/runs; v1: backend_v2/runs_v1)
# TUNING SET ONLY: refuses anything but *_t1_* (the held-out script is heldout_v2.sh). Rate 0.5 only.
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
[[ $SEQ == *_t1_* ]] || { echo "refusing $SEQ: t1 only"; exit 3; }
WS=/home/sasa/workspace/savior_ws
H=$WS/results/backend_v2
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/bv2
RATE=0.5
BACKEND=${BACKEND:-v2}
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
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8}
START=${START:-1}
if [[ $BACKEND == v1 ]]; then DSN=${DSN:-backend_v2/runs_v1}; else DSN=${DSN:-backend_v2/runs}; fi
RD=$WS/results/$DSN/$SEQ/$METHOD
mkdir -p $RD
printf '%s\n' "BACKEND=$BACKEND" "INSTALL=$INSTALL" "LAUNCH=$LAUNCH" "CFG=$CFG" "BAG=$BAG" "OVSET=$OVSET" "TOPICS=$TOPICS" "PSET=$PSET" \
  "ARGS=${ARGS[*]:-}" "OFFSETS=$OFFSETS" "START=$START" > $RD/bv2_settings_$START.txt
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $INSTALL/setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f \$R/launch.log ]] && gzip -f \$R/launch.log; i=\$((i+1)); done"
NAME="bv2_${BACKEND}_$(echo ${METHOD}_${SEQ} | tr '+' '_')_${START}_$DOM"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "$INNER"
