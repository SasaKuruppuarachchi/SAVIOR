#!/usr/bin/env bash
# run_t3.sh [steps] : PRE-REGISTERED evaluation of the t3 CONFIRMATORY split (results/t3_confirmatory/DESIGN.yaml).
# PREPARED BY THE t3 DATASET AGENT, NOT RUN. The coordinator launches it:
#     CONFIRM_T3=yes results/t3_confirmatory/scripts/run_t3.sh            (all steps)
#     CONFIRM_T3=yes results/t3_confirmatory/scripts/run_t3.sh ov2 ov2_eval      (selected steps)
# steps (default all, in this order):
#   check     md5 guards (DESIGN.yaml, backend v2, p7 frozen configs, vins FREEZE), sequence list, bags + GT present
#   ov2       OpenVINS-v2 family, 7 methods x N seq x 5 offsets, rate 0.5 (run_t3_ov2.sh via the bv2 queue)
#   ov2_eval  savior-eval multi (posyaw) + runstats per method dir (eval_bv2.sh)
#   ov2_audit validity audit (results/m2b_heldout/scripts/m2bsync.py; invalid runs are re-run, never dropped)
#   vins      per sequence: ROS 1 bag (scratch) -> frozen mask export (sens_fix1, yolo_naive, oracle_moving_ext,
#             oracle_class_ext, zero) -> VINS-Fusion family (6 methods) + DynaVINS (upstream) -> ROS 1 bag deleted
#   vins_eval savior-eval multi posyaw per method dir (src/savior/sota/scripts/eval_sota.sh)
#   analyze   pre-registered analysis (stats_t3.py): gatekeeping P1..P5, secondary, failures, cap sensitivity
# Sequences: DESIGN.yaml trajectories x L0..L3 minus EXCLUSIONS.yaml (written by the sanity step BEFORE this script, by
# the pre-written rule). Nothing is tuned: frozen perception (warehouse YOLO26 engine), frozen configs, back-end v2.
# env: PAR (OV2 containers, 12), GLOBAL_MAX (12), PAR_GPU (mask exports, 4), PAR_VINS (sequences in parallel, 3),
#      T3_ROOT (HDD data root), T3_SCRATCH (scratch: ROS 1 bags, logs, roslog), DYNAVINS_MASKS=1 (only once
#      results/dynavins_masks is frozen: refuses without results/dynavins_masks/FREEZE.md5; NOT part of the plan as frozen).
# Time / disk (estimate): OV2 96 seq x 7 x 5 = 3360 runs x ~240 s / 12 = ~19 h; VINS 96 x 7 x 5 = 3360 runs (~4 CPU each)
#   ~15 h; masks ~5 GB in results/t3_confirmatory/masks; ROS 1 bags ~1.1 GB each, at most PAR_VINS at a time.
set -euo pipefail
[[ ${CONFIRM_T3:-} == yes ]] || { echo "refusing: set CONFIRM_T3=yes (coordinator; the t3 design is frozen)"; exit 3; }
WS=/home/sasa/workspace/savior_ws
T=$WS/results/t3_confirmatory; D=$T/scripts
BV2=$WS/results/backend_v2/scripts
SO=$WS/src/savior/sota
T3_ROOT=${T3_ROOT:-/home/hdd/sasa/archive/savior/workspace/data/warehouse/t3}
export T3_SCRATCH=${T3_SCRATCH:-/tmp/claude-1002/-home-sasa-workspace-savior-ws/t3_eval}
export CONFIRM_T3 T3_ROOT
S=$T3_SCRATCH; mkdir -p $S/logs $S/bags $S/home $S/roslog
STEPS=${*:-check ov2 ov2_eval ov2_audit vins vins_eval analyze}
OV_METHODS="openvins savior_none yolo_naive sens_fix1 oracle_moving_ext oracle_class_ext savior_edge"
MASK_METHODS="sens_fix1 yolo_naive oracle_moving_ext oracle_class_ext"
OFFS="0.0 0.4 0.8 1.2 1.6"

guards() {
  (cd $T && md5sum -c --status DESIGN.md5) || { echo "refusing: DESIGN.yaml md5 mismatch"; exit 3; }
  (cd $WS/results/backend_v2 && md5sum -c --status backend_config.md5) || { echo "refusing: backend v2 md5"; exit 3; }
  (cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) || { echo "refusing: p7 md5"; exit 3; }
  (cd $WS && md5sum -c --status results/vins_savior/FREEZE.md5) || { echo "refusing: results/vins_savior/FREEZE.md5"; exit 3; }
  docker image inspect savior-sota:noetic-mask savior-sota:noetic > /dev/null || { echo "missing savior-sota images"; exit 3; }
}
seqs() {   # sequences of the design minus the pre-written-rule exclusions
  docker run --rm -i --network none -v $WS:$WS savior:humble-cuda12.8 python3 - <<'PY'
import os, yaml
T = '/home/sasa/workspace/savior_ws/results/t3_confirmatory'
D = yaml.safe_load(open(T + '/DESIGN.yaml'))
ex = set()
if os.path.isfile(T + '/EXCLUSIONS.yaml'):
    ex = {e['trajectory'] for e in (yaml.safe_load(open(T + '/EXCLUSIONS.yaml')) or {}).get('excluded', [])}
for t in D['dataset']['trajectories']:
    if t['id'] not in ex:
        for k in D['dataset']['levels']:
            print(f"{t['id']}_t3_L{k}")
PY
}
gpu_export() {   # <seq> <method> : frozen mask export (wrapper), all 5 offsets, GPU container
  local s=$1 m=$2 inst=$WS/install
  local args=(--seq $s --method $m --out $T/masks)
  [[ $m == zero ]] || args+=(--offsets $OFFS)
  docker run --rm --init -i --name "t3exp_${m}_${s}" --network none --ipc private --shm-size 8g --user "$(id -u):$(id -g)" \
    -v $WS:$WS -v $T3_ROOT:$T3_ROOT:ro -v /tmp/claude-1002:/tmp/claude-1002 -e SAVIOR_WS=$WS -e ROS_DOMAIN_ID=0 -e ROS_LOCALHOST_ONLY=1 \
    -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
    -e SAVIOR_NUM_THREADS=2 -e HOME=$S/home -e YOLO_CONFIG_DIR=$S/home/ultralytics -e ROS_LOG_DIR=$S/roslog \
    --gpus all -w $WS savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $inst/setup.bash; \
    python3 $D/export_masks_t3.py ${args[*]}" > $S/logs/export_${m}_${s}.log 2>&1
}
ros1_bag() {     # <seq> : = src/savior/sota/scripts/make_ros1_bag.sh (DATASET=warehouse) with the HDD data root mounted
  local s=$1 src=$WS/data/warehouse/ros2_stereoseg/$1 dst=$S/bags/$1.bag
  rm -f $dst
  docker run --rm -i --name "t3conv1_${s}" --network none --ipc private --user "$(id -u):$(id -g)" -v $WS:$WS -v $T3_ROOT:$T3_ROOT:ro \
    -v $S/bags:$S/bags -v $SO/scripts:$SO/scripts:ro -w /tmp savior:humble-cuda12.8 bash -c "set -e
    rosbags-convert --src $src --dst $dst --include-topic /cam0/image_raw /cam1/image_raw /imu0 \
       --src-typestore ros2_humble --dst-typestore ros1_noetic
    python3 -I $SO/scripts/verify_ros1_bag.py $src $dst" > $S/logs/ros1_$s.log 2>&1
}
vins_seq() {     # <seq> : masks + 6 VINS methods + DynaVINS for one sequence, then delete its ROS 1 bag
  local s=$1 M=$T/masks/$1
  for m in $MASK_METHODS zero; do
    [[ -f $M/$m/export_done ]] && continue
    gpu_export $s $m && touch $M/$m/export_done || echo "EXPORT FAILED $s $m"
  done
  docker run --rm -i --network none -v $WS:$WS savior:humble-cuda12.8 python3 - "$M" <<'PY' || { echo "mask check failed $s"; return 1; }
import sys, glob, yaml
f = glob.glob(sys.argv[1] + '/*/off_*/export_info.yaml')
bad = [x for x in f if yaml.safe_load(open(x))['n_fail']]
print(sys.argv[1], 'exports', len(f), '(expected 4 methods x 5 offsets = 20; zero writes none), failed:', bad); sys.exit(1 if bad or len(f) < 20 else 0)
PY
  [[ -f $S/bags/$s.bag ]] || ros1_bag $s || { echo "ROS1 BAG FAILED $s"; return 1; }
  local DET="SOTA_DETERMINISTIC=1 SOTA_IGNORE_SOLVER_TIME=1"
  while read -r tag kv; do
    ( export METHOD=vins_fusion SOTA_IMAGE=savior-sota:noetic-mask ROOT=$T/vins_runs RUNS="1 2 3 4 5" DATASET=warehouse \
        OFFSETS_FILE=$T/config/t3_offsets.txt MDIR_NAME=$tag RATE=0.5
      for x in $kv; do export "$x"; done
      $SO/scripts/run_method.sh $s $METHOD $S/bags/$s.bag ) > $S/logs/vins_${tag}_$s.log 2>&1 || echo "VINS FAILED $s $tag"
  done <<EOF
vins_fusion $DET
vins_zero $DET SOTA_MASK_DIR=$M/zero/off_all
vins_savior $DET SOTA_MASK_DIR=$M/sens_fix1/off_{off}
vins_ycls $DET SOTA_MASK_DIR=$M/yolo_naive/off_{off}
vins_odyn $DET SOTA_MASK_DIR=$M/oracle_moving_ext/off_{off}
vins_ocls $DET SOTA_MASK_DIR=$M/oracle_class_ext/off_{off}
dynavins METHOD=dynavins SOTA_IMAGE=savior-sota:noetic
EOF
  rm -f $S/bags/$s.bag
  echo "vins done $s"
}
export -f gpu_export ros1_bag vins_seq; export WS T D SO S MASK_METHODS OFFS

for step in $STEPS; do
case $step in
check)
  guards
  mapfile -t Q < <(seqs); echo "sequences: ${#Q[@]}"
  for s in "${Q[@]}"; do
    [[ -e $WS/data/warehouse/ros2_stereoseg/$s/metadata.yaml && -f $WS/data/warehouse/gt/$s.txt ]] || { echo "missing bag/GT $s"; exit 3; }
  done
  for s in "${Q[@]}"; do echo "$s ${OFFS// /,}"; done > $T/config/t3_offsets.txt.new
  if [[ -f $T/config/t3_offsets.txt ]]; then cmp -s $T/config/t3_offsets.txt.new $T/config/t3_offsets.txt || echo "NOTE: offsets file regenerated"; fi
  mv $T/config/t3_offsets.txt.new $T/config/t3_offsets.txt
  if [[ -n "${DYNAVINS_MASKS:-}" ]]; then
    [[ -f $WS/results/dynavins_masks/FREEZE.md5 ]] || { echo "refusing DYNAVINS_MASKS: results/dynavins_masks is not frozen"; exit 3; }
    echo "DYNAVINS_MASKS requested: run results/dynavins_masks/scripts/run_heldout.sh on the t3 list separately (disclosed addition)"
  fi ;;
ov2)
  guards
  J=$T/runs_jobs.txt; mkdir -p $T/runs
  { echo "# t3 OpenVINS-v2 family (generated by run_t3.sh): seq method offsets start"
    for s in $(seqs); do for m in $OV_METHODS; do echo "$s $m ${OFFS// /,} 1"; done; done; } > $J
  # heavy (YOLO) jobs first
  { grep '^#' $J; grep -v '^#' $J | grep -E ' (yolo_naive|sens_fix1|savior_edge) '; grep -v '^#' $J | grep -vE ' (yolo_naive|sens_fix1|savior_edge) '; } > $J.o && mv $J.o $J
  echo "jobs: $(grep -vc '^#' $J)"
  DSN=t3_confirmatory/runs PREFIX=t3ov_ RUNNER=$D/run_t3_ov2.sh QLOG=queue_t3.log GLOBAL_MAX=${GLOBAL_MAX:-12} \
    python3 $BV2/bv2queue.py $J ${PAR:-12} ;;
ov2_eval)
  $BV2/bpy.sh env ROOT=$T/runs $BV2/eval_bv2.sh ;;
ov2_audit)
  $BV2/bpy.sh python3 $WS/results/m2b_heldout/scripts/m2bsync.py $T/runs
  echo "invalid runs -> $T/tables/invalid.txt (re-run them, never drop)" ;;
vins)
  guards
  [[ -f $T/config/t3_offsets.txt ]] || { echo "run the check step first"; exit 3; }
  seqs | xargs -P ${PAR_VINS:-3} -I{} bash -c 'vins_seq {}' ;;
vins_eval)
  for md in $T/vins_runs/warehouse_*/*/; do ALIGNS=posyaw $SO/scripts/eval_sota.sh $md > /dev/null 2>&1 || echo "eval failed $md"; done ;;
analyze)
  docker run --rm --network none -v $WS:$WS -e MPLCONFIGDIR=/tmp savior:humble-cuda12.8 python3 -I $D/stats_t3.py
  echo "tables -> $T/tables/" ;;
*) echo "unknown step $step"; exit 2 ;;
esac
done
