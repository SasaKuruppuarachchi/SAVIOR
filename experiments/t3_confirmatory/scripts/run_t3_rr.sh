#!/usr/bin/env bash
# run_t3_rr.sh <seq> <method> <domain> : AMENDMENT_03 runner (disclosed exploratory X1-X3). Dispatcher for the bv2 queue:
#   method ovchi_best | sf1_chibest -> the review_runs variant (results/review_runs/FREEZE.yaml, md5 d00e1421..., read-only),
#   any other method             -> exec the frozen run_t3_ov2.sh unchanged.
# Settings = the frozen resolver bv2_args.py for the BASE method (openvins | sens_fix1) with the t2 proxy name, exactly as
# run_t3_ov2.sh, plus the variant's ovset_add appended in the rr_args.py way (results/review_runs/scripts/rr_args.py refuses
# t3 names, so its logic is reproduced here); the result is asserted IDENTICAL to FREEZE.yaml variants.<v>.warehouse
# (launch, cfg, ov_set, pset, launch_args, install) and the only delta to the base method is the two chi2 multipliers.
# Container / savior-run command: identical to run_t3_ov2.sh (copied below; only the settings lines differ).
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
WS=/home/sasa/workspace/savior_ws
D=$WS/results/t3_confirmatory/scripts
case $METHOD in
  ovchi_best) BASE=openvins ;;
  sf1_chibest) BASE=sens_fix1 ;;
  *) exec $D/run_t3_ov2.sh "$@" ;;
esac
H=$WS/results/backend_v2
T=$WS/results/t3_confirmatory
RR=$WS/results/review_runs
T3_ROOT=${T3_ROOT:-/home/hdd/sasa/archive/savior/workspace/data/warehouse/t3}
S=${T3_SCRATCH:-/tmp/claude-1002/-home-sasa-workspace-savior-ws/t3_eval}
[[ $SEQ == *_t3_L[0-3] ]] || { echo "t3 runner: <id>_t3_L<k> sequences only"; exit 3; }
[[ ${CONFIRM_T3:-} == yes ]] || { echo "refusing $SEQ: needs CONFIRM_T3=yes"; exit 3; }
(cd $T && md5sum -c --status DESIGN.md5) || { echo "refusing: DESIGN.yaml md5 mismatch"; exit 3; }
(cd $H && md5sum -c --status backend_config.md5) || { echo "refusing: backend_config.yaml md5 mismatch"; exit 3; }
(cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) || { echo "refusing: frozen md5"; exit 3; }
[[ $(md5sum < $RR/FREEZE.yaml | cut -c1-32) == d00e1421c1291253bfcd3bb464029ebb && ! -w $RR/FREEZE.yaml ]] || { echo "refusing: review_runs FREEZE.yaml"; exit 3; }
OFFSETS=${OFFSETS:-0.0 0.4 0.8 1.2 1.6}; DSN=${DSN:-t3_confirmatory/runs}
RATE=0.5
LEV=${SEQ##*_L}
PROXY=aisles_t2_L$LEV
mapfile -t L < <(python3 $H/scripts/bv2_args.py $PROXY $BASE v2)
[[ ${#L[@]} -ge 8 ]] || { echo "bv2_args failed"; exit 2; }
[[ ${L[3]} == $WS/data/warehouse/ros2_stereoseg/$PROXY && ${L[4]} == $WS/data/warehouse/gt/$PROXY.txt ]] \
  || { echo "unexpected proxy bag/gt lines"; exit 2; }
for k in 0 1 2 5 6 7 "${!L[@]}"; do
  [[ $k -eq 3 || $k -eq 4 ]] && continue
  [[ ${L[$k]} != *aisles_t2* ]] || { echo "setting line $k depends on the sequence name: ${L[$k]}"; exit 2; }
done
BASE_OVSET=${L[5]}
# variant delta (rr_args.py settings(): ovset_add appended, keys must be new) + assert == FREEZE.yaml
mapfile -t V < <(python3 - "$RR/FREEZE.yaml" "$METHOD" "$BASE" "${L[@]}" <<'PY'
import sys, yaml
fz, var, base, L = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
F = yaml.safe_load(open(fz))['variants'][var]
assert F['base'] == base and F['scope'] == 'heldout' and not F.get('pset_set'), var
o = {}
for it in L[5].split():
    k, _, v = it.partition('=')
    assert k not in o
    o[k] = v
for k, x in F['ovset_add'].items():
    assert k not in o, k
    o[k] = str(x)
ovset = ' '.join(f'{k}={x}' for k, x in o.items())
W = F['warehouse']
assert W['launch'] == L[1] and W['cfg'] == L[2] and W['install'] == L[0], 'launch/cfg/install differ from FREEZE.yaml'
assert W['ov_set'] == ovset, (W['ov_set'], ovset)
assert W['pset'] == L[7], 'pset differs from FREEZE.yaml'
assert list(W['launch_args'] or []) == L[8:], 'launch args differ from FREEZE.yaml'
assert sorted(F['ovset_add']) == ['up_msckf_chi2_multipler', 'up_slam_chi2_multipler']
print(ovset)
PY
)
[[ ${#V[@]} -eq 1 && -n ${V[0]} ]] || { echo "variant settings check failed"; exit 2; }
L[5]=${V[0]}
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
if [[ -n ${RR_DRYRUN:-} ]]; then printf '%s\n' "LAUNCH=$LAUNCH" "CFG=$CFG" "INSTALL=$INSTALL" "OVSET=$OVSET" "TOPICS=$TOPICS" "PSET=$PSET" "LA=${LA[*]}"; exit 0; fi   # settings only
START=${START:-1}
RD=$WS/results/$DSN/$SEQ/$METHOD
mkdir -p $RD $S/roslog $S/home
printf '%s\n' "PROXY=$PROXY" "VARIANT=$METHOD BASE=$BASE BASE_OVSET=$BASE_OVSET" "INSTALL=$INSTALL" "LAUNCH=$LAUNCH" "CFG=$CFG" "BAG=$BAG" "GT=$GTF" "OVSET=$OVSET" \
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
