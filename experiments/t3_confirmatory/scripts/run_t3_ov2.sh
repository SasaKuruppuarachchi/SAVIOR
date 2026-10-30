#!/usr/bin/env bash
# run_t3_ov2.sh <seq> <method> <domain> -> results/<DSN>/<seq>/<method>/run_XX   (t3 CONFIRMATORY runner, OpenVINS-v2 family)
# Same container / savior-run protocol as results/backend_v2/scripts/run_heldout_v2.sh (rate 0.5, back-end v2, frozen
# perception). Settings are resolved by the UNCHANGED frozen resolver results/backend_v2/scripts/bv2_args.py, called with
# the t2 proxy name aisles_t2_L<k> of the same level (the frozen resolvers recognise warehouse sequences by the names
# aisles_/hall_/dock_; for warehouse sequences every setting except the bag and GT paths is independent of the name, which
# is asserted here); only BAG and GT are replaced by the t3 sequence's. The t3 bags live on the HDD (symlinks in
# data/warehouse/ros2_stereoseg), so the t3 data root is mounted read-only into the container.
# Refuses unless CONFIRM_T3=yes and the frozen md5s (t3 DESIGN.yaml, backend v2, p7) verify.
# env: OFFSETS (default: the 5 pre-registered offsets), START (1), DSN (t3_confirmatory/runs), SANITY=1 (sanity runs:
#      openvins / oracle_moving_ext only, offsets 0.0 0.3 0.6, DSN t3_confirmatory/sanity; allowed before CONFIRM_T3).
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
WS=/home/sasa/workspace/savior_ws
H=$WS/results/backend_v2
T=$WS/results/t3_confirmatory
T3_ROOT=${T3_ROOT:-/home/hdd/sasa/archive/savior/workspace/data/warehouse/t3}
S=${T3_SCRATCH:-/tmp/claude-1002/-home-sasa-workspace-savior-ws/t3_eval}
[[ $SEQ == *_t3_L[0-3] ]] || { echo "t3 runner: <id>_t3_L<k> sequences only"; exit 3; }
(cd $T && md5sum -c --status DESIGN.md5) || { echo "refusing: results/t3_confirmatory/DESIGN.yaml md5 mismatch"; exit 3; }
(cd $H && md5sum -c --status backend_config.md5) || { echo "refusing: backend_config.yaml md5 mismatch"; exit 3; }
(cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) || { echo "refusing: frozen md5"; exit 3; }
if [[ -n "${SANITY:-}" ]]; then
  [[ $METHOD == openvins || $METHOD == oracle_moving_ext ]] || { echo "sanity: openvins / oracle_moving_ext only"; exit 3; }
  OFFSETS=${OFFSETS:-0.0 0.3 0.6}; DSN=${DSN:-t3_confirmatory/sanity}
else
  [[ ${CONFIRM_T3:-} == yes ]] || { echo "refusing $SEQ: the t3 evaluation needs CONFIRM_T3=yes (coordinator)"; exit 3; }
  OFFSETS=${OFFSETS:-0.0 0.4 0.8 1.2 1.6}; DSN=${DSN:-t3_confirmatory/runs}
fi
RATE=0.5
LEV=${SEQ##*_L}
PROXY=aisles_t2_L$LEV
mapfile -t L < <(python3 $H/scripts/bv2_args.py $PROXY $METHOD v2)
[[ ${#L[@]} -ge 8 ]] || { echo "bv2_args failed"; exit 2; }
[[ ${L[3]} == $WS/data/warehouse/ros2_stereoseg/$PROXY && ${L[4]} == $WS/data/warehouse/gt/$PROXY.txt ]] \
  || { echo "unexpected proxy bag/gt lines"; exit 2; }
for k in 0 1 2 5 6 7 "${!L[@]}"; do
  [[ $k -eq 3 || $k -eq 4 ]] && continue
  [[ ${L[$k]} != *aisles_t2* ]] || { echo "setting line $k depends on the sequence name: ${L[$k]}"; exit 2; }
done
INSTALL=${L[0]}; LAUNCH=${L[1]}; CFG=${L[2]}; OVSET=${L[5]}; TOPICS=${L[6]}; PSET=${L[7]}
BAG=$WS/data/warehouse/ros2_stereoseg/$SEQ; GTF=$WS/data/warehouse/gt/$SEQ.txt
[[ -e $BAG/metadata.yaml && -f $GTF ]] || { echo "missing bag / GT for $SEQ"; exit 2; }
ARGS=("${L[@]:8}")
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$PSET")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
START=${START:-1}
RD=$WS/results/$DSN/$SEQ/$METHOD
mkdir -p $RD $S/roslog $S/home
printf '%s\n' "PROXY=$PROXY" "INSTALL=$INSTALL" "LAUNCH=$LAUNCH" "CFG=$CFG" "BAG=$BAG" "GT=$GTF" "OVSET=$OVSET" \
  "TOPICS=$TOPICS" "PSET=$PSET" "ARGS=${ARGS[*]:-}" "OFFSETS=$OFFSETS" "START=$START" > $RD/t3_settings_$START.txt
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $INSTALL/setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f \$R/launch.log ]] && gzip -f \$R/launch.log; i=\$((i+1)); done"
NAME="t3ov_$(echo ${METHOD}_${SEQ} | tr '+' '_')_${START}_$DOM"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -v $T3_ROOT:$T3_ROOT:ro -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "$INNER"
