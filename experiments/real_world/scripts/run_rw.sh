#!/usr/bin/env bash
# run_rw.sh <seq> <method> <domain> -> results/real_world/runs/<seq>/<method>/run_XX (one isolated container, offsets in series)
# Real-world study (Monado MSD Valve Index). Settings from rw_args.py (frozen final_config + addendum VIODE/COCO methods;
# dataset I/O only). Same container / savior-run protocol as results/backend_v2/scripts/run_bv2.sh (mask_policy
# wait 30 s, feature_stats auto, deterministic_processing; rate 0.25 for the masked methods, PROTOCOL.yaml). diag_openvins: P5 diagnostic overlay + SAVIOR_DIAG_FILE.
# env: OFFSETS (default 0.0..1.8 s), START (1)
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
WS=/home/sasa/workspace/savior_ws
H=$WS/results/real_world
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/rw
DIAGOVL=/home/hdd/sasa/archive/savior/scratchpad/agentI/diag_ws/install   # = scratchpad/agentI (archived, symlink); P5 diagnostic overlay
DEFRATE=0.25   # FREEZE_AMENDMENT 2 (A5): every method at rate 0.25 (was 0.5 for openvins, savior_none, diag_openvins)
RATE=${RATE:-$DEFRATE}
mapfile -t L < <(python3 $H/scripts/rw_args.py $SEQ $METHOD)
[[ ${#L[@]} -ge 8 ]] || { echo "rw_args failed"; exit 2; }
INSTALL=${L[0]}; LAUNCH=${L[1]}; CFG=${L[2]}; BAG=${L[3]}; OVSET=${L[5]}; TOPICS=${L[6]}; PSET=${L[7]}
BAG=${BAG_OVERRIDE:-$BAG}   # smoke tests only (results/real_world/smoke)
ARGS=("${L[@]:8}")
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$PSET")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
OFFSETS=${OFFSETS:-0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8}
START=${START:-1}
DSN=${DSN:-real_world/runs}
RD=$WS/results/$DSN/$SEQ/$METHOD
mkdir -p $RD $S/roslog $S/home
OVL=""; DIAGX=""
if [[ $METHOD == diag_openvins ]]; then OVL="source $DIAGOVL/setup.bash;"; DIAGX="export SAVIOR_DIAG_FILE=\$R/diag_updates.csv;"; fi
printf '%s\n' "INSTALL=$INSTALL" "OVERLAY=${OVL}" "LAUNCH=$LAUNCH" "CFG=$CFG" "BAG=$BAG" "OVSET=$OVSET" "TOPICS=$TOPICS" "PSET=$PSET" \
  "ARGS=${ARGS[*]:-}" "OFFSETS=$OFFSETS" "START=$START" "RATE=$RATE" > $RD/rw_settings_$START.txt
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $INSTALL/setup.bash; $OVL set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; $DIAGX \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f \$R/launch.log ]] && gzip -f \$R/launch.log; \
  [[ -f \$R/diag_updates.csv ]] && gzip -f \$R/diag_updates.csv; i=\$((i+1)); done"
NAME="rw_${METHOD}_${SEQ}_${START}_$DOM"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 -v /home/hdd/sasa/archive/savior/scratchpad/agentI:/home/hdd/sasa/archive/savior/scratchpad/agentI:ro \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "$INNER"
