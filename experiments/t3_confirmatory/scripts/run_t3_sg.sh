#!/usr/bin/env bash
# run_t3_sg.sh <seq> <method> <domain> : AMENDMENT_04 runner (disclosed exploratory Y1-Y4). Dispatcher for the bv2 queue:
#   method sf1_nis | ov_nis | savior_sg -> results/semantic_gate/FREEZE.yaml (md5 0457d646..., read-only) methods.<m>,
#   any other method -> exec run_t3_rr.sh (which runs ovchi_best / sf1_chibest, or the frozen run_t3_ov2.sh unchanged).
# Settings = results/semantic_gate/scripts/sg_args.py settings() (imported read-only; its __main__ refuses non-t1 names, so it
# is called with the t2 proxy name of the same level exactly as run_t3_ov2.sh calls bv2_args.py), asserted IDENTICAL to
# FREEZE.yaml methods.<m>.warehouse_t1_instantiation (install, launch, cfg, ov_set, pset, launch_args) and to base + the
# frozen delta only (pset_set / ovset_add keys). Binary install results/semantic_gate/install (read-only, md5s of the three
# binaries asserted). Container / savior-run command identical to run_t3_ov2.sh.
set -euo pipefail
SEQ=$1; METHOD=$2; DOM=$3
WS=/home/sasa/workspace/savior_ws
D=$WS/results/t3_confirmatory/scripts
case $METHOD in
  sf1_nis|savior_sg) BASE=sens_fix1 ;;
  ov_nis) BASE=openvins ;;
  *) exec $D/run_t3_rr.sh "$@" ;;
esac
SG=$WS/results/semantic_gate
H=$WS/results/backend_v2
T=$WS/results/t3_confirmatory
T3_ROOT=${T3_ROOT:-/home/hdd/sasa/archive/savior/workspace/data/warehouse/t3}
S=${T3_SCRATCH:-/tmp/claude-1002/-home-sasa-workspace-savior-ws/t3_eval}
[[ $SEQ == *_t3_L[0-3] ]] || { echo "t3 runner: <id>_t3_L<k> sequences only"; exit 3; }
[[ ${CONFIRM_T3:-} == yes ]] || { echo "refusing $SEQ: needs CONFIRM_T3=yes"; exit 3; }
(cd $T && md5sum -c --status DESIGN.md5) || { echo "refusing: DESIGN.yaml md5 mismatch"; exit 3; }
(cd $H && md5sum -c --status backend_config.md5) || { echo "refusing: backend_config.yaml md5 mismatch"; exit 3; }
(cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) || { echo "refusing: frozen md5"; exit 3; }
[[ $(md5sum < $SG/FREEZE.yaml | cut -c1-32) == 0457d646d61995b1de656cdd86ecb5bc && ! -w $SG/FREEZE.yaml ]] || { echo "refusing: semantic_gate FREEZE.yaml"; exit 3; }
[[ $(md5sum < $SG/install/ov_msckf/lib/ov_msckf/run_subscribe_msckf | cut -c1-32) == 4f0be6c294c2398f79af0084ed2ea62b && \
   $(md5sum < $SG/install/ov_msckf/lib/libov_msckf_lib.so | cut -c1-32) == 5e2ddca0b7baae5392fbe52d5ab2eeaa && \
   $(md5sum < $SG/install/ov_core/lib/libov_core_lib.so | cut -c1-32) == cafc5a8b9ef10f8393e7a111324dfb7b ]] || { echo "refusing: SG install md5"; exit 3; }
OFFSETS=${OFFSETS:-0.0 0.4 0.8 1.2 1.6}; DSN=${DSN:-t3_confirmatory/runs}
RATE=0.5
LEV=${SEQ##*_L}
PROXY=aisles_t2_L$LEV
mapfile -t B < <(python3 $H/scripts/bv2_args.py $PROXY $BASE v2)
[[ ${#B[@]} -ge 8 ]] || { echo "bv2_args failed"; exit 2; }
mapfile -t L < <(python3 - "$SG/FREEZE.yaml" "$METHOD" "$BASE" "$PROXY" "${B[@]}" <<'PY'
import sys, yaml
fz, var, base, proxy, B = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:]
sys.path.insert(0, '/home/sasa/workspace/savior_ws/results/semantic_gate/scripts')
import sg_args
F = yaml.safe_load(open(fz))['methods'][var]
assert F['base'] == base and F['variant'] == var or (var == 'savior_sg' and F['variant'] == 'sg_s025_b025_kb0'), var
L = sg_args.settings(proxy, F['variant'])
W = F['warehouse_t1_instantiation']
assert W['install'] == L[0] == sg_args.SG_INSTALL and W['launch'] == L[1] and W['cfg'] == L[2], 'install/launch/cfg differ from FREEZE.yaml'
assert W['ov_set'] == L[5] and W['pset'] == L[7] and list(W['launch_args'] or []) == L[8:], 'settings differ from FREEZE.yaml'
assert L[3:5] == B[3:5] and L[6] == B[6] and L[8:] == B[8:] and L[1:3] == B[1:3], 'non-delta line differs from the base'
kv = lambda s: dict(x.partition('=')[::2] for x in s.split())  # noqa: E731
ob, ov = kv(B[5]), kv(L[5])
assert {k: v for k, v in ov.items() if k not in ob} == {k: sg_args.fmt(x) for k, x in F['ovset_add'].items()} and all(ov[k] == ob[k] for k in ob), 'ov_set delta'
pb, pv = kv(B[7]), kv(L[7])
assert {k: v for k, v in pv.items() if pb.get(k) != v} == {k: sg_args.fmt(x) for k, x in (F['pset_set'] or {}).items()} and set(pb) <= set(pv), 'pset delta'
print('\n'.join(L))
PY
)
[[ ${#L[@]} -ge 8 && ${L[0]} == $SG/install ]] || { echo "SG settings check failed"; exit 2; }
[[ ${L[3]} == $WS/data/warehouse/ros2_stereoseg/$PROXY && ${L[4]} == $WS/data/warehouse/gt/$PROXY.txt ]] \
  || { echo "unexpected proxy bag/gt lines"; exit 2; }
for k in 0 1 2 5 6 7 "${!L[@]}"; do
  [[ $k -eq 3 || $k -eq 4 ]] && continue
  [[ ${L[$k]} != *aisles_t2* ]] || { echo "setting line $k depends on the sequence name: ${L[$k]}"; exit 2; }
done
BASE_OVSET=${B[5]}
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
