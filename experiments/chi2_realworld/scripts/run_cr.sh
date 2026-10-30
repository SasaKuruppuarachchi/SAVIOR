#!/usr/bin/env bash
# run_cr.sh <seq> <variant> <domain> -> results/chi2_realworld/runs/<seq>/<variant>/run_XX  (one isolated container, offsets in series)
# chi2-realworld (one-shot check of the frozen review_runs ovchi_best / sf1_chibest on Monado). Adapted from
# results/nis_validation/scripts/run_nv.sh (copy in scripts/from_nis_validation/); container / savior-run protocol identical to the
# paired baselines' runner results/real_world/scripts/run_rw.sh (rate 0.25, mask_policy wait 30 s, feature_stats auto, topics
# passed, workspace install/). Settings from cr_args.py (asserts PROTOCOL.yaml). env: OFFSETS (space list, required), START (1).
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
WS=/home/sasa/workspace/savior_ws
CR=$WS/results/chi2_realworld
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/cr
(cd $CR && md5sum -c --status PROTOCOL.md5) || { echo "refusing: PROTOCOL.yaml md5"; exit 3; }
[[ $(md5sum < $WS/results/review_runs/FREEZE.yaml | cut -d' ' -f1) == d00e1421c1291253bfcd3bb464029ebb ]] || { echo "refusing: review FREEZE md5"; exit 3; }
[[ $(md5sum < $CR/DECISION_RULE.txt | cut -d' ' -f1) == ad5789081473e4cc36909ddd6ac319f8 ]] || { echo "refusing: DECISION_RULE md5"; exit 3; }
(cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) || { echo "refusing: frozen md5"; exit 3; }
RATE=0.25
mapfile -t L < <(python3 $CR/scripts/cr_args.py $SEQ $METHOD)
[[ ${#L[@]} -ge 8 ]] || { echo "cr_args failed"; exit 2; }
INSTALL=${L[0]}; LAUNCH=${L[1]}; CFG=${L[2]}; BAG=${L[3]}; OVSET=${L[5]}; TOPICS=${L[6]}; PSET=${L[7]}
ARGS=("${L[@]:8}")
LA=(--launch-arg rate:=$RATE --launch-arg feature_stats:=auto --launch-arg "ov_set:=$OVSET" --launch-arg "topics:=$TOPICS")
if [[ $LAUNCH == savior.launch.py ]]; then
  LA+=(--launch-arg mask_policy:=wait --launch-arg mask_timeout_ms:=30000)
  [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=$PSET")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "$a"); done
: "${OFFSETS:?OFFSETS required}"
START=${START:-1}
DSN=chi2_realworld/runs
RD=$WS/results/$DSN/$SEQ/$METHOD
mkdir -p $RD $S/roslog $S/home
printf '%s\n' "VARIANT=$METHOD" "INSTALL=$INSTALL" "OVERLAY=" "LAUNCH=$LAUNCH" "CFG=$CFG" "BAG=$BAG" "OVSET=$OVSET" \
  "TOPICS=$TOPICS" "PSET=$PSET" "ARGS=${ARGS[*]:-}" "OFFSETS=$OFFSETS" "START=$START" "RATE=$RATE" > $RD/cr_settings_$START.txt
INNER="export ROS_LOG_DIR=$S/roslog; source /opt/ros/humble/setup.bash; source $INSTALL/setup.bash; set -e; i=$START; for off in $OFFSETS; do \
  R=$RD/run_\$(printf %02d \$i); mkdir -p \$R; \
  savior-run --launch-pkg savior_bringup --launch-file $LAUNCH --bag $BAG --config $CFG -n 1 --start-index \$i --results-root $WS/results \
  --dataset $DSN --seq $SEQ --method $METHOD --rate $RATE --domain-id $DOM --cooldown 1 --launch-arg start_offset:=\$off $(printf '%q ' "${LA[@]}") || echo \"run \$i failed\"; \
  [[ -f \$R/savior_stats.jsonl ]] && gzip -f \$R/savior_stats.jsonl; [[ -f \$R/launch.log ]] && gzip -f \$R/launch.log; i=\$((i+1)); done"
NAME="cr_${METHOD}_${SEQ}_${START}_$DOM"
exec docker run --rm --init -i --name "$NAME" --network none --ipc private --shm-size 8g \
  -v $WS:$WS -e SAVIOR_WS=$WS -e SAVIOR_PLATFORM=amd64 -e ROS_DOMAIN_ID=$DOM -e ROS_LOCALHOST_ONLY=1 \
  -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
  -e SAVIOR_NUM_THREADS=2 -e YOLO_CONFIG_DIR=$S/home/ultralytics -e MPLCONFIGDIR=$S/home/mpl \
  -e HOME=$S/home -v /tmp/claude-1002:/tmp/claude-1002 \
  --gpus all -w $WS savior:humble-cuda12.8 bash -c "$INNER"
