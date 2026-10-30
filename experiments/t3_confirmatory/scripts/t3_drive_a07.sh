#!/usr/bin/env bash
# t3_drive_a07.sh : = t3_drive_a06.sh (DRIVER_A06.md5) with the VINS step run by vins_seq_fixed() below instead of
# 'run_t3.sh vins'. BUG in the frozen run_t3.sh vins_seq: the 7 VINS-family methods are read with 'while read ... <<EOF' and
# run_method.sh -> drun_sota.sh uses 'docker run -i', so the container's stdin is the REST OF THE HEREDOC; rosbag play reads
# keys from stdin ('space' = toggle pause) and paused after ~3 frames in every run (6/6 first runs hung at 4 frontend rows for
# > 1 h, 0 % CPU; and the heredoc lines would be consumed, skipping the remaining methods). vins_seq_fixed() is vins_seq
# verbatim (same exports, mask check, ROS 1 bag, the same 7 method dirs with the same env as the heredoc table, via
# t3_drive.sh vins_env) with stdin from /dev/null and a per-sequence .done marker. No setting changes. No VINS run had completed.
# t3_drive_a06.sh : the VINS phase of t3_drive_a05.sh (AMENDMENT_05_IMPL.md5), restarted with more parallelism and nothing else
# changed. t3_drive_a05.sh completed the OV family (planned + A03 + A04, audits, re-runs: 5760/5760 clarified-valid) and had
# just started the VINS step (only mask exports had run, no VINS / DynaVINS run). It was stopped because PAR_VINS 3 (the
# run_t3.sh default) means ~80 h. Execution parameters only: PAR_VINS=6 (run_t3.sh env, documented there) and PAR_DM=5,
# total still <= 12 t3 containers. Still blinded: no analysis.
# t3_drive_a05.sh : = t3_drive_a04.sh (AMENDMENT_04_IMPL.md5) with the AMENDMENT_05 frame-rule clarification: the frames audit
# (t3_frames_audit.py, AMENDMENT_05_IMPL.md5) reports strict and clarified counts; the OV re-run set = (m2bsync invalid.txt minus runs
# that are tail-only in the frames audit AND sync ok in m2bsync) + frames-audit clarified invalid; tail-only runs are NOT re-run.
# Still blinded: no analysis. t3_drive_a04.sh was stopped while waiting for the planned OV2 queue.
# t3_drive_a04.sh : = t3_drive_a03b.sh (AMENDMENT_03_IMPL.md5) + the AMENDMENT_04 queue (3 x 96 x 5 = 1440 runs: sf1_nis,
# ov_nis, savior_sg via run_t3_sg.sh) right after the AMENDMENT_03 queue, and the OV re-run dispatcher run_t3_sg.sh (which passes
# every other method to run_t3_rr.sh / run_t3_ov2.sh unchanged). Still blinded: no analysis. t3_drive_a03b.sh was stopped while
# waiting for the planned OV2 queue.
# t3_drive_a03b.sh : = t3_drive_a03.sh (AMENDMENT_03_IMPL.md5) WITHOUT the analysis step (coordinator blinding instruction
# 2026-10-27 ~09:20, before any t3 outcome was computed: runs, eval, audits and re-runs only; analyze waits for the coordinator's go).
# t3_drive_a03.sh was stopped while still waiting for the planned OV2 queue. Original header:
# t3_drive_a03.sh : continuation of t3_drive.sh (AMENDMENT_02_IMPL.md5, unchanged) with AMENDMENT_03 inserted. Written while the
# planned OV2 queue (run_t3.sh check ov2 ov2_eval ov2_audit, started by t3_drive.sh) was running and before any t3 result was
# evaluated or looked at. t3_drive.sh itself was stopped (its run_t3.sh child continues untouched); its functions are reused
# verbatim (sourced), with one substitution: the OV re-run queue uses the dispatcher run_t3_rr.sh (= run_t3_ov2.sh for every
# planned method, the review_runs settings for ovchi_best / sf1_chibest).
# Order: wait for run_t3.sh ov steps -> AMENDMENT_03 queue (2 x 96 x 5 = 960 runs, after the planned OV2 jobs, <= 12
# containers) -> eval -> OV-family audits + re-runs (m2bsync + frames audit, all 9 methods, <= 3 attempts) -> VINS step +
# DynaVINS+masks -> VINS / DynaVINS re-runs -> analysis (stats_t3.py, t3_extras.py, t3_amend03.py).
set -uo pipefail
D0=/home/sasa/workspace/savior_ws/results/t3_confirmatory/scripts
source <(sed -n '1,/^for ph in/p' $D0/t3_drive.sh | sed '$d' | sed 's#RUNNER=\$D/run_t3_ov2.sh#RUNNER=$D/run_t3_sg.sh#')
type ov_rerun | grep -q 'RUNNER=$D/run_t3_sg.sh' || { echo "ov_rerun substitution failed"; exit 2; }
ov_rerun() {   # AMENDMENT_05 version of t3_drive.sh ov_rerun (same structure; selection excludes tail-only runs)
  local att seq m run i dirs
  for att in 1 2 3; do
    $BV2/bpy.sh python3 $WS/results/m2b_heldout/scripts/m2bsync.py $T/runs > $S/logs/m2bsync_pre$att.log 2>&1
    cp $T/tables/invalid.txt $S/invalid_attempts/m2bsync_invalid_before_att$att.txt
    faudit _ov --vins /nonexistent
    cp $T/tables/frames_invalid_ov.txt $S/invalid_attempts/frames_invalid_ov_before_att$att.txt
    cp $T/tables/frames_tail_only_ov.txt $S/invalid_attempts/frames_tail_only_ov_before_att$att.txt
    python3 - $T/tables/invalid.txt $T/tables/sync_audit.csv $T/tables/frames_tail_only_ov.txt $T/tables/frames_invalid_ov.txt \
        $S/invalid_attempts/ov_union_att$att.txt $S/invalid_attempts/ov_tailskip_att$att.txt <<'PY'
import csv, sys
inv, sync, tail, fr, out, skip = sys.argv[1:]
key = lambda l: tuple(l.split()[-3:])  # noqa: E731
m2b = {key(l) for l in open(inv) if l.strip()}
ok_sync = {(r['seq'], r['method'], r['run']) for r in csv.DictReader(open(sync)) if r['sync_ok'] == '1'}
tl = {key(l) for l in open(tail) if l.strip()}
skipped = sorted(k for k in m2b if k in tl and k in ok_sync)
sel = sorted((m2b - set(skipped)) | {key(l) for l in open(fr) if l.strip()})
open(out, 'w').write(''.join(' '.join(k) + '\n' for k in sel))
open(skip, 'w').write(''.join(' '.join(k) + '\n' for k in skipped))
PY
    say "OV attempt $att: $(wc -l < $S/invalid_attempts/ov_union_att$att.txt) runs to re-run (m2bsync $(wc -l < $T/tables/invalid.txt), of which tail-only + sync ok not re-run $(wc -l < $S/invalid_attempts/ov_tailskip_att$att.txt); frames clarified-invalid $(wc -l < $T/tables/frames_invalid_ov.txt), tail-only $(wc -l < $T/tables/frames_tail_only_ov.txt))"
    [[ -s $S/invalid_attempts/ov_union_att$att.txt ]] || return 0
    : > $S/rerun_ov_att$att.txt; dirs=()
    while read -r seq m run; do
      i=$((10#${run#run_})); mkdir -p $S/invalid_attempts/ov_att$att/$seq/$m
      mv $T/runs/$seq/$m/$run $S/invalid_attempts/ov_att$att/$seq/$m/ 2>/dev/null
      echo "$seq $m ${OFFS[$((i-1))]} $i" >> $S/rerun_ov_att$att.txt; dirs+=($T/runs/$seq/$m)
    done < $S/invalid_attempts/ov_union_att$att.txt
    DSN=t3_confirmatory/runs PREFIX=t3ov_ RUNNER=$D/run_t3_sg.sh QLOG=queue_t3_rerun$att.log GLOBAL_MAX=$GLOBAL_MAX \
      python3 $BV2/bv2queue.py $S/rerun_ov_att$att.txt 12
    $BV2/bpy.sh env ROOT=$T/runs $BV2/eval_bv2.sh $(printf '%s\n' "${dirs[@]}" | sort -u) > $S/logs/eval_rerun_ov$att.log 2>&1
  done
  $BV2/bpy.sh python3 $WS/results/m2b_heldout/scripts/m2bsync.py $T/runs > $S/logs/m2bsync_final.log 2>&1
  faudit _ov --vins /nonexistent
  say "OV after 3 attempts: m2bsync $(wc -l < $T/tables/invalid.txt), frames clarified-invalid $(wc -l < $T/tables/frames_invalid_ov.txt), tail-only $(wc -l < $T/tables/frames_tail_only_ov.txt) (reported)"
}
MASK_METHODS="sens_fix1 yolo_naive oracle_moving_ext oracle_class_ext"
OFFS_S="0.0 0.4 0.8 1.2 1.6"
gpu_export() {   # = run_t3.sh gpu_export (verbatim), stdin /dev/null
  local s=$1 m=$2 inst=$WS/install
  local args=(--seq $s --method $m --out $T/masks)
  [[ $m == zero ]] || args+=(--offsets $OFFS_S)
  docker run --rm --init -i --name "t3exp_${m}_${s}" --network none --ipc private --shm-size 8g --user "$(id -u):$(id -g)" \
    -v $WS:$WS -v $T3_ROOT:$T3_ROOT:ro -v /tmp/claude-1002:/tmp/claude-1002 -e SAVIOR_WS=$WS -e ROS_DOMAIN_ID=0 -e ROS_LOCALHOST_ONLY=1 \
    -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4 -e NUMEXPR_NUM_THREADS=2 \
    -e SAVIOR_NUM_THREADS=2 -e HOME=$S/home -e YOLO_CONFIG_DIR=$S/home/ultralytics -e ROS_LOG_DIR=$S/roslog \
    --gpus all -w $WS savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $inst/setup.bash; \
    python3 $D/export_masks_t3.py ${args[*]}" < /dev/null > $S/logs/export_${m}_${s}.log 2>&1
}
vins_seq_fixed() {   # = run_t3.sh vins_seq with stdin /dev/null for every container
  local s=$1 M=$T/masks/$1 m tag
  [[ -f $T/vins_runs/warehouse_$s/.done ]] && { echo "vins done $s (already)"; return 0; }
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
  [[ -f $S/bags/$s.bag ]] || ros1_bag $s $S/bags < /dev/null || { echo "ROS1 BAG FAILED $s"; return 1; }
  for tag in vins_fusion vins_zero vins_savior vins_ycls vins_odyn vins_ocls dynavins; do
    ( export METHOD=vins_fusion SOTA_IMAGE=savior-sota:noetic-mask ROOT=$T/vins_runs RUNS="1 2 3 4 5" DATASET=warehouse \
        OFFSETS_FILE=$T/config/t3_offsets.txt MDIR_NAME=$tag RATE=0.5
      for x in $(vins_env $tag $s); do export "$x"; done
      $SO/scripts/run_method.sh $s $METHOD $S/bags/$s.bag ) < /dev/null > $S/logs/vins_${tag}_$s.log 2>&1 || echo "VINS FAILED $s $tag"
  done
  rm -f $S/bags/$s.bag
  touch $T/vins_runs/warehouse_$s/.done
  echo "vins done $s"
}
say "t3_drive_a07 started (VINS phase; PAR_VINS=${PAR_VINS:-6} PAR_DM=$PAR_DM)"
say "phase vins: run_t3.sh vins vins_eval, DynaVINS+masks concurrently"
dm_all > $S/logs/dm_all.log 2>&1 & DMP=$!
$D/run_t3.sh check >> $S/logs/run_t3_vins.log 2>&1 || { say "run_t3.sh check failed"; exit 3; }
VP=()
for s in $(seqs); do
  while :; do   # at most PAR_VINS sequences at a time (own PIDs only; dm_all is a separate job)
    n=0; for p in "${VP[@]}"; do kill -0 $p 2>/dev/null && n=$((n+1)); done
    (( n < ${PAR_VINS:-6} )) && break; sleep 30
  done
  vins_seq_fixed $s < /dev/null >> $S/logs/run_t3_vins.log 2>&1 & VP+=($!)
done
for p in "${VP[@]}"; do wait $p; done
say "VINS runs done (vins_seq_fixed)"
$D/run_t3.sh vins_eval >> $S/logs/run_t3_vins.log 2>&1 || say "run_t3.sh vins_eval rc=$?"
say "VINS step done; waiting for DynaVINS+masks"
wait $DMP
bag_rerun vins
bag_rerun dyna
$BV2/bpy.sh python3 $WS/results/m2b_heldout/scripts/m2bsync.py $T/runs > $S/logs/m2bsync_final_all.log 2>&1
faudit "" --dyna $T/dyna_masks_runs
say "t3_drive_a07 finished (runs + audits only; NO analysis, blinded until the coordinator's go)"
