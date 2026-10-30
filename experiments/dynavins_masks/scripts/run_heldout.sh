#!/usr/bin/env bash
# run_heldout.sh [steps] : HELD-OUT evaluation of DynaVINS + SAVIOR masks (patch P10) on warehouse t2 (12 seq) and VIODE
# (12 seq). Run ONCE, after the freeze:   DM_HELDOUT_GO=1 results/dynavins_masks/scripts/run_heldout.sh
#   steps: check bags runs eval analyze clean (default: all, in this order)
# Fixed before any held-out run (checked here, refuses on mismatch):
#   results/p7/final_config{,_addendum}.md5   (perception methods the masks were exported with)
#   results/vins_savior/FREEZE.md5            (mask exporter, P9 harness, offsets; the held-out masks were exported under it)
#   results/dynavins_masks/FREEZE.md5         (P10 patch, image build files, DynaVINS configs, harness, this script,
#                                              analysis, held-out mask manifest)
#   image savior-sota:noetic-mask-dyna        (COMMITS.txt P10 md5 == patches/dynavins_savior_mask.patch)
#   held-out masks                            (every export_info.yaml masks_md5 == validation/heldout_masks_manifest.txt)
# Settings (= the t1 protocol, REPORT.md): DynaVINS upstream configs src/savior/sota/config/<warehouse|viode>/dynavins
#   (unchanged, NOT retuned), rate 0.5, frozen offsets (src/savior/sota/scripts/<warehouse|viode>_offsets.txt), every
#   DynaVINS method incl. the plain baseline in deterministic mode (savior_deterministic 1, savior_ignore_solver_time 1,
#   savior_solver_threads 1); gate mode threshold 128 / relaxed 224 / min features 30 (P9 defaults);
#   masks = results/vins_savior/heldout/masks (sens_fix1 = SAVIOR, yolo_naive = Y-Cls, oracle_moving_ext = O-Dyn+B,
#   oracle_class_ext = O-Cls+B, zero = empty-mask control). Plain DynaVINS is re-run in deterministic mode (the M3b
#   results/sota DynaVINS runs are upstream-threaded and used only as the upstream reference 'dyna_up').
# Resources: <= 8 containers (PAR_RUN), scratch bags deleted by 'clean'.
set -euo pipefail
[[ ${DM_HELDOUT_GO:-} == 1 ]] || { echo "refusing: set DM_HELDOUT_GO=1 (after the freeze)"; exit 3; }
WS=/home/sasa/workspace/savior_ws; R=$WS/results/dynavins_masks; SC=$R/scripts; SO=$WS/src/savior/sota
HM=$WS/results/vins_savior/heldout/masks
export DM_SCRATCH=${DM_SCRATCH:-/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/dm}
PAR_RUN=${PAR_RUN:-8}
STEPS=${*:-check bags runs eval analyze clean}
LOG=$DM_SCRATCH/logs; mkdir -p $LOG $DM_SCRATCH/bags
T2=(aisles_t2_L0 aisles_t2_L1 aisles_t2_L2 aisles_t2_L3 hall_t2_L0 hall_t2_L1 hall_t2_L2 hall_t2_L3 dock_t2_L0 dock_t2_L1 dock_t2_L2 dock_t2_L3)
VI=(parking_lot_none parking_lot_low parking_lot_mid parking_lot_high city_day_none city_day_low city_day_mid city_day_high
    city_night_none city_night_low city_night_mid city_night_high)
dset() { [[ $1 == *_t2_* ]] && echo t2 || echo viode; }
check() {
  (cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) \
    || { echo "refusing: frozen p7 config md5 mismatch"; exit 3; }
  (cd $WS && md5sum -c --status results/vins_savior/FREEZE.md5) || { echo "refusing: vins_savior FREEZE.md5 mismatch"; exit 3; }
  (cd $WS && md5sum -c --status $R/FREEZE.md5) || { echo "refusing: results/dynavins_masks/FREEZE.md5 mismatch"; exit 3; }
  local want got
  want=$(md5sum $SO/patches/dynavins_savior_mask.patch | cut -c1-32)
  got=$(docker run --rm --network none savior-sota:noetic-mask-dyna awk '$1=="P10"{print $3}' /opt/sota/COMMITS.txt)
  [[ $want == "$got" ]] || { echo "refusing: image P10 md5 $got != patch $want (rebuild build_mask_dyna.sh)"; exit 3; }
  local n=0 cur
  while read -r dir md5; do   # export_info masks_md5 (= md5 over stamp + per-frame pixel md5s); zero: md5 of index.csv
    if [[ -f $HM/$dir/export_info.yaml ]]; then cur=$(awk '$1=="masks_md5:"{print $2}' $HM/$dir/export_info.yaml)
    else cur=$(md5sum < $HM/$dir/index.csv | cut -c1-32); fi
    [[ $cur == "$md5" ]] || { echo "refusing: mask $dir changed"; exit 3; }; n=$((n + 1))
  done < <(grep -v '^#' $R/validation/heldout_masks_manifest.txt)
  [[ $n == 1224 ]] || { echo "refusing: manifest has $n entries (expected 24 x (5 x 10 + 1) = 1224)"; exit 3; }
  echo "freeze check ok"
}
for step in $STEPS; do
case $step in
check) check ;;
bags)  check
  for s in "${T2[@]}"; do echo "warehouse $s"; done > $DM_SCRATCH/bagjobs.txt
  for s in "${VI[@]}"; do echo "viode $s"; done >> $DM_SCRATCH/bagjobs.txt
  xargs -P 3 -L 1 bash -c '[[ -f $DM_SCRATCH/bags/$1.bag ]] || DATASET=$0 '$SO'/scripts/make_ros1_bag.sh $1 $DM_SCRATCH/bags/$1.bag > '$LOG'/bag_$1.log 2>&1; tail -1 '$LOG'/bag_$1.log' \
    < $DM_SCRATCH/bagjobs.txt ;;
runs)  check
  DET="SOTA_DETERMINISTIC=1 SOTA_IGNORE_SOLVER_TIME=1 SOTA_SOLVER_THREADS=1"; J=$DM_SCRATCH/jobs_heldout.txt; : > $J
  for s in "${T2[@]}" "${VI[@]}"; do d=$(dset $s)
    echo "$d $s dyna_det $DET" >> $J
    echo "$d $s dyna_zero $DET SOTA_MASK_DIR=$HM/$s/zero/off_all" >> $J
    echo "$d $s dyna_savior $DET SOTA_MASK_DIR=$HM/$s/sens_fix1/off_{off}" >> $J
    echo "$d $s dyna_ycls $DET SOTA_MASK_DIR=$HM/$s/yolo_naive/off_{off}" >> $J
    echo "$d $s dyna_odyn $DET SOTA_MASK_DIR=$HM/$s/oracle_moving_ext/off_{off}" >> $J
    echo "$d $s dyna_ocls $DET SOTA_MASK_DIR=$HM/$s/oracle_class_ext/off_{off}" >> $J
  done
  cp $J $R/scripts/jobs_heldout.txt
  DM_HELDOUT_GO=1 $SC/queue.sh $J $PAR_RUN ;;
eval)  # posyaw (protocol), one container per sequence, PAR_RUN at a time
  for d in t2 viode; do for sd in $R/runs_$d/*/; do echo $sd; done; done | \
    xargs -P $PAR_RUN -I{} bash -c 'ALIGNS=posyaw '$SO'/scripts/eval_sota.sh {}*/ > /dev/null 2>&1 || echo "eval failed {}"' ;;
analyze)
  for d in t2 viode; do
    for met in ate rpe; do
      docker run --rm --network none --user "$(id -u):$(id -g)" -v $WS:$WS -e MPLCONFIGDIR=/tmp savior:humble-cuda12.8 python3 $SC/dm_analyze.py \
        --dataset $d --metric $met --root runs_$d --out tables_$d --up-root $WS/results/sota > /dev/null; done
    docker run --rm --network none --user "$(id -u):$(id -g)" -v $WS:$WS savior:humble-cuda12.8 python3 $SC/dm_control.py runs_$d tables_$d > /dev/null
  done
  echo "tables: $R/tables_t2 $R/tables_viode" ;;
clean) rm -rf $DM_SCRATCH/bags ;;
*) echo "unknown step $step"; exit 2 ;;
esac
done
