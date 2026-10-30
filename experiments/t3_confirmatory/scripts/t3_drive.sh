#!/usr/bin/env bash
# t3_drive.sh [phase ...] : coordinator-side driver of the ONE t3 confirmatory evaluation (results/t3_confirmatory), written
# before any t3 run (md5 in AMENDMENT_02_IMPL.md5). It only CALLS the frozen scripts (run_t3.sh, run_t3_ov2.sh, bv2queue.py,
# eval_bv2.sh, m2bsync.py, run_method.sh, eval_sota.sh, run_method_dm.sh, stats_t3.py) and adds the AMENDMENT_02 rules:
#   s1  frames audit (scripts/t3_frames_audit.py) for every family; runs failing it OR the frozen m2bsync audit are moved
#       aside (scratch, kept) and re-run UNCHANGED, at most 3 attempts; anything still invalid is reported, never dropped.
#   s2  <= 12 t3 containers in total (bv2queue GLOBAL_MAX 12 on t3ov_*; VINS PAR_VINS 3; DynaVINS+masks gated below).
#   s3  DynaVINS + SAVIOR masks (results/dynavins_masks run_heldout.sh logic: P10 image savior-sota:noetic-mask-dyna,
#       deterministic, 1 solver thread; dyna_det + dyna_zero/savior/ycls/odyn/ocls) on the t3 list with the t3 offsets and
#       the t3 mask exports -> results/t3_confirmatory/dyna_masks_runs. Started together with the VINS step; a sequence is
#       run once its 5 mask exports are complete. Exploratory, outside P1-P5 / S1-S14.
# phases (default all): ov  vins  rerun_vins  rerun_dyna  analyze      (dyna runs concurrently with vins)
set -uo pipefail
export CONFIRM_T3=yes
WS=/home/sasa/workspace/savior_ws; T=$WS/results/t3_confirmatory; D=$T/scripts
BV2=$WS/results/backend_v2/scripts; SO=$WS/src/savior/sota; DMR=$WS/results/dynavins_masks
export T3_ROOT=${T3_ROOT:-/home/hdd/sasa/archive/savior/workspace/data/warehouse/t3}
export T3_SCRATCH=${T3_SCRATCH:-/tmp/claude-1002/-home-sasa-workspace-savior-ws/t3_eval}
S=$T3_SCRATCH; DL=$S/drive.log; mkdir -p $S/logs/dm $S/bags $S/dm_bags $S/invalid_attempts
OFFS=(0.0 0.4 0.8 1.2 1.6)
GLOBAL_MAX=${GLOBAL_MAX:-12}; PAR_DM=${PAR_DM:-6}
PHASES=${*:-ov vins rerun_vins rerun_dyna analyze}
say() { echo "$(date '+%F %T') $*" | tee -a $DL; }
seqs() { awk '{print $1}' $T/config/t3_offsets.txt; }
ncont() { docker ps --format '{{.Names}}' | grep -cE '^(t3|sota_.*_t3_L[0-3]|dm_.*_t3_L[0-3])' ; }
ndm() { docker ps --format '{{.Names}}' | grep -cE '^dm_dyna_.*_t3_L[0-3]' ; }
gate() {   # wait for a container slot: total t3 containers < GLOBAL_MAX and DynaVINS+masks containers < $1
  local lim=$1
  while :; do
    exec 9> $S/gate.lock; flock 9
    if (( $(ncont) < GLOBAL_MAX && $(ndm) < lim )); then return 0; fi   # caller releases the lock after starting
    flock -u 9; sleep 20
  done
}
release() { sleep 8; flock -u 9; }
faudit() {  # <tag> <args...> : frames audit in the savior image (data read-only)
  local tag=$1; shift
  docker run --rm --name t3fa_${tag#_}_$$ --network none --user "$(id -u):$(id -g)" -v $WS:$WS -v $T3_ROOT:$T3_ROOT:ro \
    savior:humble-cuda12.8 python3 -I $D/t3_frames_audit.py --tag $tag "$@" > $S/logs/faudit$tag.log 2>&1
  tail -2 $S/logs/faudit$tag.log | tee -a $DL
}
ros1_bag() {   # <seq> <dir> : = run_t3.sh ros1_bag (same container command), into <dir>
  local s=$1 src=$WS/data/warehouse/ros2_stereoseg/$1 dst=$2/$1.bag
  rm -f $dst
  docker run --rm -i --name "t3conv1_${s}_$$" --network none --ipc private --user "$(id -u):$(id -g)" -v $WS:$WS -v $T3_ROOT:$T3_ROOT:ro \
    -v $2:$2 -v $SO/scripts:$SO/scripts:ro -w /tmp savior:humble-cuda12.8 bash -c "set -e
    rosbags-convert --src $src --dst $dst --include-topic /cam0/image_raw /cam1/image_raw /imu0 \
       --src-typestore ros2_humble --dst-typestore ros1_noetic
    python3 -I $SO/scripts/verify_ros1_bag.py $src $dst" > $S/logs/ros1_$(basename $2)_$s.log 2>&1
}
vins_env() {   # <tag> <seq> : the env of run_t3.sh vins_seq for one VINS-family method dir
  local M=$T/masks/$2 DET="SOTA_DETERMINISTIC=1 SOTA_IGNORE_SOLVER_TIME=1"
  case $1 in
    vins_fusion) echo "$DET" ;;
    vins_zero) echo "$DET SOTA_MASK_DIR=$M/zero/off_all" ;;
    vins_savior) echo "$DET SOTA_MASK_DIR=$M/sens_fix1/off_{off}" ;;
    vins_ycls) echo "$DET SOTA_MASK_DIR=$M/yolo_naive/off_{off}" ;;
    vins_odyn) echo "$DET SOTA_MASK_DIR=$M/oracle_moving_ext/off_{off}" ;;
    vins_ocls) echo "$DET SOTA_MASK_DIR=$M/oracle_class_ext/off_{off}" ;;
    dynavins) echo "METHOD=dynavins SOTA_IMAGE=savior-sota:noetic" ;;
  esac
}
dm_env() {     # <tag> <seq> : = results/dynavins_masks/scripts/run_heldout.sh runs step, t3 masks
  local M=$T/masks/$2 DET="SOTA_DETERMINISTIC=1 SOTA_IGNORE_SOLVER_TIME=1 SOTA_SOLVER_THREADS=1"
  case $1 in
    dyna_det) echo "$DET" ;;
    dyna_zero) echo "$DET SOTA_MASK_DIR=$M/zero/off_all" ;;
    dyna_savior) echo "$DET SOTA_MASK_DIR=$M/sens_fix1/off_{off}" ;;
    dyna_ycls) echo "$DET SOTA_MASK_DIR=$M/yolo_naive/off_{off}" ;;
    dyna_odyn) echo "$DET SOTA_MASK_DIR=$M/oracle_moving_ext/off_{off}" ;;
    dyna_ocls) echo "$DET SOTA_MASK_DIR=$M/oracle_class_ext/off_{off}" ;;
  esac
}
vins_run() {   # <seq> <tag> <runs "1 2 .."> : one VINS-family container (run_method.sh, as run_t3.sh vins_seq)
  ( export METHOD=vins_fusion SOTA_IMAGE=savior-sota:noetic-mask ROOT=$T/vins_runs RUNS="$3" DATASET=warehouse \
      OFFSETS_FILE=$T/config/t3_offsets.txt MDIR_NAME=$2 RATE=0.5
    for x in $(vins_env $2 $1); do export "$x"; done
    $SO/scripts/run_method.sh $1 $METHOD $S/bags/$1.bag ) >> $S/logs/rerun_vins_${2}_$1.log 2>&1
}
dm_run() {     # <seq> <tag> <runs> : one DynaVINS+masks container (= dmrun.sh with the t3 root / offsets)
  ( export METHOD=dynavins SOTA_IMAGE=savior-sota:noetic-mask-dyna ROOT=$T/dyna_masks_runs RUNS="$3" DATASET=warehouse \
      OFFSETS_FILE=$T/config/t3_offsets.txt MDIR_NAME=$2 RATE=0.5
    for x in $(dm_env $2 $1); do export "$x"; done
    $SO/scripts/run_method_dm.sh $1 $METHOD $S/dm_bags/$1.bag ) >> $S/logs/dm/run_${2}_$1.log 2>&1
}
dm_check() {   # = run_heldout.sh check, minus the t2 mask manifest (t3 masks are checked per sequence instead)
  (cd $WS/results/p7 && md5sum -c --status final_config.md5 && md5sum -c --status final_config_addendum.md5) || { say "DM refusing: p7 md5"; return 3; }
  (cd $WS && md5sum -c --status results/vins_savior/FREEZE.md5) || { say "DM refusing: vins_savior FREEZE"; return 3; }
  local bad; bad=$(cd $WS && md5sum -c $DMR/FREEZE.md5 2>/dev/null | grep -v ': OK$' | grep -v '^results/dynavins_masks/scripts/dm_figs.py: FAILED$')
  [[ -z $bad ]] || { say "DM refusing: dynavins_masks FREEZE: $bad"; return 3; }
  local want got
  want=$(md5sum $SO/patches/dynavins_savior_mask.patch | cut -c1-32)
  got=$(docker run --rm --network none savior-sota:noetic-mask-dyna awk '$1=="P10"{print $3}' /opt/sota/COMMITS.txt)
  [[ $want == "$got" ]] || { say "DM refusing: image P10 $got != $want"; return 3; }
  say "DM freeze check ok (only mismatch: layout-only dm_figs.py, disclosed in AMENDMENT_02)"
}
masks_ready() {   # <seq> : 5 export_done markers and 20 export_info.yaml with n_fail 0
  local M=$T/masks/$1 m n
  for m in sens_fix1 yolo_naive oracle_moving_ext oracle_class_ext zero; do [[ -f $M/$m/export_done ]] || return 1; done
  n=$(grep -h '^n_fail:' $M/*/off_*/export_info.yaml 2>/dev/null | awk '$2==0' | wc -l)
  [[ $n -ge 20 ]]
}
dm_seq() {   # <seq> : bag -> 6 DynaVINS+masks containers (5 offsets each) -> bag deleted -> eval
  local s=$1 tag pids=()
  gate $PAR_DM; ros1_bag $s $S/dm_bags & local bp=$!; release; wait $bp || { say "DM bag failed $s"; return 1; }
  for tag in dyna_det dyna_zero dyna_savior dyna_ycls dyna_odyn dyna_ocls; do
    gate $PAR_DM; dm_run $s $tag "1 2 3 4 5" & pids+=($!); release
  done
  wait "${pids[@]}"
  rm -f $S/dm_bags/$s.bag
  ALIGNS=posyaw $SO/scripts/eval_sota.sh $T/dyna_masks_runs/warehouse_$s/*/ > /dev/null 2>&1 || say "DM eval failed $s"
  say "DM done $s"
}
dm_all() {
  dm_check || return 3
  local s pending; mapfile -t pending < <(seqs)
  while ((${#pending[@]})); do
    local left=()
    for s in "${pending[@]}"; do
      if [[ -f $T/dyna_masks_runs/warehouse_$s/.done ]]; then continue; fi
      if masks_ready $s; then
        while (( $(jobs -rp | wc -l) >= 2 )); do wait -n; done      # at most 2 sequences (bags) at a time
        ( dm_seq $s && touch $T/dyna_masks_runs/warehouse_$s/.done ) &
      else left+=($s); fi
    done
    pending=("${left[@]}")
    ((${#pending[@]})) && sleep 120
  done
  wait
  say "DM all sequences done"
}
ov_rerun() {   # up to 3 attempts of the union of m2bsync invalid.txt and frames-audit invalid runs (OpenVINS-v2 family)
  local att l seq m run i dirs
  for att in 1 2 3; do
    $BV2/bpy.sh python3 $WS/results/m2b_heldout/scripts/m2bsync.py $T/runs > $S/logs/m2bsync_pre$att.log 2>&1
    cp $T/tables/invalid.txt $S/invalid_attempts/m2bsync_invalid_before_att$att.txt
    faudit _ov --vins /nonexistent
    cp $T/tables/frames_invalid_ov.txt $S/invalid_attempts/frames_invalid_ov_before_att$att.txt
    { cat $T/tables/invalid.txt; awk '{print $2, $3, $4}' $T/tables/frames_invalid_ov.txt; } | sort -u > $S/invalid_attempts/ov_union_att$att.txt
    say "OV attempt $att: $(wc -l < $S/invalid_attempts/ov_union_att$att.txt) invalid runs (m2bsync $(wc -l < $T/tables/invalid.txt), frames $(wc -l < $T/tables/frames_invalid_ov.txt))"
    [[ -s $S/invalid_attempts/ov_union_att$att.txt ]] || return 0
    : > $S/rerun_ov_att$att.txt; dirs=()
    while read -r seq m run; do
      i=$((10#${run#run_})); mkdir -p $S/invalid_attempts/ov_att$att/$seq/$m
      mv $T/runs/$seq/$m/$run $S/invalid_attempts/ov_att$att/$seq/$m/ 2>/dev/null
      echo "$seq $m ${OFFS[$((i-1))]} $i" >> $S/rerun_ov_att$att.txt; dirs+=($T/runs/$seq/$m)
    done < $S/invalid_attempts/ov_union_att$att.txt
    DSN=t3_confirmatory/runs PREFIX=t3ov_ RUNNER=$D/run_t3_ov2.sh QLOG=queue_t3_rerun$att.log GLOBAL_MAX=$GLOBAL_MAX \
      python3 $BV2/bv2queue.py $S/rerun_ov_att$att.txt 12
    $BV2/bpy.sh env ROOT=$T/runs $BV2/eval_bv2.sh $(printf '%s\n' "${dirs[@]}" | sort -u) > $S/logs/eval_rerun_ov$att.log 2>&1
  done
  $BV2/bpy.sh python3 $WS/results/m2b_heldout/scripts/m2bsync.py $T/runs > $S/logs/m2bsync_final.log 2>&1
  faudit _ov --vins /nonexistent
  say "OV after 3 attempts: m2bsync $(wc -l < $T/tables/invalid.txt), frames $(wc -l < $T/tables/frames_invalid_ov.txt) still invalid (reported)"
}
bag_rerun() {  # <family vins|dyna> : up to 3 attempts of the frames-audit invalid runs, unchanged
  local fam=$1 att tag seq run i s
  local root=$T/vins_runs bd=$S/bags fa="--ov /nonexistent --vins $T/vins_runs"
  [[ $fam == dyna ]] && { root=$T/dyna_masks_runs; bd=$S/dm_bags; fa="--ov /nonexistent --vins /nonexistent --dyna $T/dyna_masks_runs"; }
  for att in 1 2 3 4; do
    faudit _$fam $fa
    cp $T/tables/frames_invalid_$fam.txt $S/invalid_attempts/frames_invalid_${fam}_before_att$att.txt
    say "$fam attempt $att: $(wc -l < $T/tables/frames_invalid_$fam.txt) frame-rule invalid runs"
    [[ -s $T/tables/frames_invalid_$fam.txt && $att -le 3 ]] || break
    for s in $(awk '{print $2}' $T/tables/frames_invalid_$fam.txt | sort -u); do
      ( gate 99; ros1_bag $s $bd & bp=$!; release; wait $bp
        for tag in $(awk -v s=$s '$2==s{print $3}' $T/tables/frames_invalid_$fam.txt | sort -u); do
          runs=$(awk -v s=$s -v t=$tag '$2==s && $3==t{sub("run_", "", $4); print $4+0}' $T/tables/frames_invalid_$fam.txt | tr '\n' ' ')
          for i in $runs; do mkdir -p $S/invalid_attempts/${fam}_att$att/warehouse_$s/$tag
            mv $root/warehouse_$s/$tag/run_$(printf %02d $i) $S/invalid_attempts/${fam}_att$att/warehouse_$s/$tag/ 2>/dev/null; done
          gate 99
          if [[ $fam == vins ]]; then vins_run $s $tag "$runs" & else dm_run $s $tag "$runs" & fi
          p=$!; release; wait $p
        done
        rm -f $bd/$s.bag
        ALIGNS=posyaw $SO/scripts/eval_sota.sh $root/warehouse_$s/*/ > /dev/null 2>&1 || say "eval failed $fam $s" ) &
      while (( $(jobs -rp | wc -l) >= 3 )); do wait -n; done
    done
    wait
  done
}

for ph in $PHASES; do
case $ph in
ov)
  say "phase ov: run_t3.sh check ov2 ov2_eval ov2_audit"
  $D/run_t3.sh check ov2 ov2_eval ov2_audit >> $S/logs/run_t3_ov.log 2>&1 || { say "run_t3.sh ov steps failed rc=$?"; exit 1; }
  ov_rerun ;;
vins)
  say "phase vins: run_t3.sh vins vins_eval, DynaVINS+masks concurrently"
  dm_all > $S/logs/dm_all.log 2>&1 & DMP=$!
  $D/run_t3.sh vins >> $S/logs/run_t3_vins.log 2>&1 || say "run_t3.sh vins rc=$?"
  $D/run_t3.sh vins_eval >> $S/logs/run_t3_vins.log 2>&1 || say "run_t3.sh vins_eval rc=$?"
  say "VINS step done; waiting for DynaVINS+masks"
  wait $DMP ;;
rerun_vins) bag_rerun vins ;;
rerun_dyna) bag_rerun dyna ;;
analyze)
  $BV2/bpy.sh python3 $WS/results/m2b_heldout/scripts/m2bsync.py $T/runs > $S/logs/m2bsync_analyze.log 2>&1
  $D/run_t3.sh analyze > $S/logs/analyze.log 2>&1 || say "analyze rc=$?"
  docker run --rm --name t3extras_$$ --network none --user "$(id -u):$(id -g)" -v $WS:$WS -e MPLCONFIGDIR=/tmp savior:humble-cuda12.8 \
    python3 -I $D/t3_extras.py > $S/logs/extras.log 2>&1 || say "extras rc=$?"
  faudit "" --dyna $T/dyna_masks_runs
  say "analysis done" ;;
*) say "unknown phase $ph"; exit 2 ;;
esac
done
say "drive finished: $PHASES"
