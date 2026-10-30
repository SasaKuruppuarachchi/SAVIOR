#!/usr/bin/env bash
# run_heldout.sh : HELD-OUT evaluation of VINS-Fusion + SAVIOR masks on warehouse t2 (12 seq) and VIODE (12 seq).
# PREPARED BY THE VINS-SAVIOR AGENT, NOT RUN. To be launched by the coordinator AFTER the freeze:
#     VS_HELDOUT_GO=1 results/vins_savior/scripts/heldout/run_heldout.sh [steps]      steps: bags masks runs eval analyze clean
#                                                                                       (default: all, in this order)
# Everything is fixed by files frozen before any held-out run (checked here, refuses on mismatch):
#   results/p7/final_config.yaml (6fea24e5...), final_config_addendum.yaml (f07c9c30...)  - perception methods
#   results/vins_savior/FREEZE.md5 - P9 patch, mask exporter, harness, VINS configs, this script, analysis
# Settings (identical to the t1 protocol, results/vins_savior/REPORT.md):
#   masks  : export_masks.py, per start offset; methods sens_fix1, savior_edge (frozen_edge/install), yolo_naive,
#            oracle_moving_ext, oracle_class_ext (+ zero); VIODE uses the frozen VIODE instantiation of the addendum
#   VINS   : savior-sota:noetic-mask, src/savior/sota/config/<warehouse|viode>/vins_fusion (no change), rate 0.5,
#            savior_deterministic=1 + savior_ignore_solver_time=1 for every VINS method incl. the baseline;
#            gate mode threshold 128 / relaxed 224 / min features 30; SAVIOR-edge deferred, latency 250 ms
#   offsets: src/savior/sota/scripts/{warehouse,viode}_offsets.txt (= frozen protocol offsets)
#   DynaVINS: the M3b runs in results/sota (same offsets, rate 0.5, upstream) are reused (RERUN_DYNAVINS=1 re-runs)
#   stats  : vs_analyze.py --dataset t2|viode (failure > 2 m warehouse / > 1 m VIODE, cap 10 m, paired, bootstrap,
#            Wilcoxon, Holm; pose-count rule)
# Resources: <= 10 containers (PAR_GPU exports on the GPU, PAR_RUN VINS containers), scratch bags deleted by 'clean'.
set -euo pipefail
[[ ${VS_HELDOUT_GO:-} == 1 ]] || { echo "refusing: set VS_HELDOUT_GO=1 (coordinator, after the freeze)"; exit 3; }
WS=/home/sasa/workspace/savior_ws; V=$WS/results/vins_savior; H=$V/heldout; SC=$V/scripts; SO=$WS/src/savior/sota
export VS_SCRATCH=${VS_SCRATCH:-/tmp/claude-1002/-home-sasa-workspace-savior-ws/vins_savior_heldout}
PAR_GPU=${PAR_GPU:-6}; PAR_RUN=${PAR_RUN:-9}
STEPS=${*:-bags masks runs eval analyze clean}
(cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) \
  || { echo "refusing: frozen p7 config md5 mismatch"; exit 3; }
(cd $WS && md5sum -c --status $V/FREEZE.md5) || { echo "refusing: results/vins_savior/FREEZE.md5 mismatch"; exit 3; }
docker image inspect savior-sota:noetic-mask > /dev/null || { echo "build src/savior/sota/build_mask.sh first"; exit 3; }
mkdir -p $H $VS_SCRATCH/bags $VS_SCRATCH/logs $VS_SCRATCH/home
LOG=$VS_SCRATCH/logs
T2=(aisles_t2_L0 aisles_t2_L1 aisles_t2_L2 aisles_t2_L3 hall_t2_L0 hall_t2_L1 hall_t2_L2 hall_t2_L3 dock_t2_L0 dock_t2_L1 dock_t2_L2 dock_t2_L3)
VI=(parking_lot_none parking_lot_low parking_lot_mid parking_lot_high city_day_none city_day_low city_day_mid city_day_high
    city_night_none city_night_low city_night_mid city_night_high)
MASKM=(sens_fix1 savior_edge yolo_naive oracle_moving_ext oracle_class_ext)
offs() { awk -v s=$1 '$1==s{gsub(",", " ", $2); print $2}' $SO/scripts/$2_offsets.txt; }
dset() { [[ $1 == *_t2_* ]] && echo t2 || echo viode; }
dsname() { [[ $1 == *_t2_* ]] && echo warehouse || echo viode; }

gpu_export() {  # <seq> <method> : one GPU container, all offsets of the sequence
  local s=$1 m=$2 inst=$WS/install o
  [[ $m == savior_edge ]] && inst=$WS/frozen_edge/install
  o=$(offs $s $(dsname $s))
  docker run --rm --init -i --name "vsh_exp_${m}_${s}" --network none --ipc private --shm-size 8g --user "$(id -u):$(id -g)" \
    -v $WS:$WS -v /tmp/claude-1002:/tmp/claude-1002 -e SAVIOR_WS=$WS -e ROS_DOMAIN_ID=0 -e ROS_LOCALHOST_ONLY=1 \
    -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
    -e SAVIOR_NUM_THREADS=2 -e HOME=$VS_SCRATCH/home -e YOLO_CONFIG_DIR=$VS_SCRATCH/home/ultralytics -e ROS_LOG_DIR=$VS_SCRATCH/roslog \
    --gpus all -w $WS savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $inst/setup.bash; \
    python3 $SO/mask_export/export_masks.py --seq $s --method $m --offsets $o --out $H/masks" > $LOG/export_${m}_${s}.log 2>&1
}
export -f gpu_export offs dsname; export WS V H SO LOG

for step in $STEPS; do
case $step in
bags)   # ROS 1 bags (cam0, cam1, imu0; verified) in scratch
  for s in "${T2[@]}"; do echo "warehouse $s"; done > $VS_SCRATCH/bagjobs.txt
  for s in "${VI[@]}"; do echo "viode $s"; done >> $VS_SCRATCH/bagjobs.txt
  xargs -P 3 -L 1 bash -c '[[ -f $VS_SCRATCH/bags/$1.bag ]] || DATASET=$0 '$SO'/scripts/make_ros1_bag.sh $1 $VS_SCRATCH/bags/$1.bag > '$LOG'/bag_$1.log 2>&1; tail -1 '$LOG'/bag_$1.log' \
    < $VS_SCRATCH/bagjobs.txt ;;
masks)  # per-offset SAVIOR masks (+ zero control) -> results/vins_savior/heldout/masks
  T2_ALL=("${T2[@]}"); [[ -n "${VS_MASKS_VIODE_ONLY:-}" ]] && T2=()   # re-export after the 2026-10-25 VIODE reader fix
  for m in "${MASKM[@]}"; do for s in "${T2[@]}" "${VI[@]}"; do echo "$s $m"; done; done | xargs -P $PAR_GPU -L 1 bash -c 'gpu_export $0 $1; tail -2 $LOG/export_$1_$0.log'
  for s in "${T2[@]}" "${VI[@]}"; do
    $SC/srun.sh "hzero_$s" $WS/install python3 $SO/mask_export/export_masks.py --seq $s --method zero --out $H/masks; done
  # completeness: every method x seq x offset has export_info.yaml with n_fail 0
  docker run --rm -i --network none -v $WS:$WS savior:humble-cuda12.8 python3 - "$H/masks" <<'PY'
import sys, glob, yaml
bad = [f for f in glob.glob(sys.argv[1] + '/*/*/off_*/export_info.yaml') if yaml.safe_load(open(f))['n_fail']]
n = len(glob.glob(sys.argv[1] + '/*/*/off_*/export_info.yaml'))
print('exports', n, '(expected 24 seq x 5 methods x 10 offsets = 1200), with failed frames:', bad); sys.exit(1 if bad or n < 1200 else 0)
PY
  T2=("${T2_ALL[@]}") ;;
runs)   # 6 VINS methods (+ zero-mask control); DynaVINS reused from results/sota unless RERUN_DYNAVINS=1
  DET="SOTA_DETERMINISTIC=1 SOTA_IGNORE_SOLVER_TIME=1"; M=$H/masks; J=$VS_SCRATCH/jobs_runs.txt; : > $J
  for s in "${T2[@]}" "${VI[@]}"; do d=$(dset $s)
    echo "$d $s vins_fusion $DET" >> $J
    echo "$d $s vins_zero $DET SOTA_MASK_DIR=$M/$s/zero/off_all" >> $J
    echo "$d $s vins_savior $DET SOTA_MASK_DIR=$M/$s/sens_fix1/off_{off}" >> $J
    echo "$d $s vins_edge $DET SOTA_MASK_DIR=$M/$s/savior_edge/off_{off} SOTA_MASK_MODE=deferred SOTA_MASK_LATENCY_MS=250" >> $J
    echo "$d $s vins_ycls $DET SOTA_MASK_DIR=$M/$s/yolo_naive/off_{off}" >> $J
    echo "$d $s vins_odyn $DET SOTA_MASK_DIR=$M/$s/oracle_moving_ext/off_{off}" >> $J
    echo "$d $s vins_ocls $DET SOTA_MASK_DIR=$M/$s/oracle_class_ext/off_{off}" >> $J
    [[ -n "${RERUN_DYNAVINS:-}" ]] && echo "$d $s dynavins METHOD=dynavins SOTA_IMAGE=savior-sota:noetic" >> $J
  done
  xargs -P $PAR_RUN -L 1 bash -c 'VS_HELDOUT_GO=1 '$H'/../scripts/heldout/hvrun.sh "$@" > '$LOG'/run_$1_$2_$3.log 2>&1; echo "done $1 $2 $3"' _ < $J ;;
eval)   # savior-eval multi, posyaw (protocol)
  for d in t2 viode; do
    for md in $H/runs_$d/*/*/; do ALIGNS=posyaw $SO/scripts/eval_sota.sh $md > /dev/null 2>&1 || echo "eval failed $md"; done; done ;;
analyze)
  for d in t2 viode; do DR=$WS/results/sota; [[ -n "${RERUN_DYNAVINS:-}" ]] && DR=$H/runs_$d
    for met in ate rpe; do
      docker run --rm --network none -v $WS:$WS -e MPLCONFIGDIR=/tmp savior:humble-cuda12.8 python3 $SC/vs_analyze.py \
        --dataset $d --metric $met --root heldout/runs_$d --out heldout/tables_$d --dynavins-root $DR > /dev/null; done
    docker run --rm --network none -v $WS:$WS savior:humble-cuda12.8 python3 $SC/vs_control.py heldout/runs_$d heldout/tables_$d $d
  done
  echo "tables: $H/tables_t2 $H/tables_viode" ;;
clean) rm -rf $VS_SCRATCH/bags ;;
*) echo "unknown step $step"; exit 2 ;;
esac
done
