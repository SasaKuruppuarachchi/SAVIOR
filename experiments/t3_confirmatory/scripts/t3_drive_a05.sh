#!/usr/bin/env bash
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
say "t3_drive_a05 started; waiting for run_t3.sh check ov2 ov2_eval ov2_audit"
while pgrep -f 'run_t3.sh check ov2 ov2_eval ov2_audit' > /dev/null; do sleep 120; done
grep -q 'invalid' $S/logs/run_t3_ov.log 2>/dev/null || say "WARNING: run_t3.sh ov log has no audit line"
say "AMENDMENT_03 queue"
J=$T/runs_jobs_a03.txt
{ echo "# AMENDMENT_03 (t3_drive_a03.sh): seq method offsets start"
  OC=$(IFS=,; echo "${OFFS[*]}")
  for m in sf1_chibest ovchi_best; do for s in $(seqs); do echo "$s $m $OC 1"; done; done; } > $J
say "A03 jobs: $(grep -vc '^#' $J)"
DSN=t3_confirmatory/runs PREFIX=t3ov_ RUNNER=$D/run_t3_rr.sh QLOG=queue_t3_a03.log GLOBAL_MAX=$GLOBAL_MAX \
  python3 $BV2/bv2queue.py $J 12
$BV2/bpy.sh env ROOT=$T/runs $BV2/eval_bv2.sh $T/runs/*/ovchi_best/ $T/runs/*/sf1_chibest/ > $S/logs/eval_a03.log 2>&1
say "A03 runs + eval done"
say "AMENDMENT_04 queue"
J4=$T/runs_jobs_a04.txt
{ echo "# AMENDMENT_04 (t3_drive_a04.sh): seq method offsets start"
  for m in sf1_nis savior_sg ov_nis; do for s in $(seqs); do echo "$s $m $OC 1"; done; done; } > $J4
say "A04 jobs: $(grep -vc '^#' $J4)"
DSN=t3_confirmatory/runs PREFIX=t3ov_ RUNNER=$D/run_t3_sg.sh QLOG=queue_t3_a04.log GLOBAL_MAX=$GLOBAL_MAX \
  python3 $BV2/bv2queue.py $J4 12
$BV2/bpy.sh env ROOT=$T/runs $BV2/eval_bv2.sh $T/runs/*/sf1_nis/ $T/runs/*/ov_nis/ $T/runs/*/savior_sg/ > $S/logs/eval_a04.log 2>&1
say "A04 runs + eval done"
ov_rerun
say "phase vins: run_t3.sh vins vins_eval, DynaVINS+masks concurrently"
dm_all > $S/logs/dm_all.log 2>&1 & DMP=$!
$D/run_t3.sh vins >> $S/logs/run_t3_vins.log 2>&1 || say "run_t3.sh vins rc=$?"
$D/run_t3.sh vins_eval >> $S/logs/run_t3_vins.log 2>&1 || say "run_t3.sh vins_eval rc=$?"
say "VINS step done; waiting for DynaVINS+masks"
wait $DMP
bag_rerun vins
bag_rerun dyna
$BV2/bpy.sh python3 $WS/results/m2b_heldout/scripts/m2bsync.py $T/runs > $S/logs/m2bsync_final_all.log 2>&1
faudit "" --dyna $T/dyna_masks_runs
say "t3_drive_a05 finished (runs + audits only; NO analysis, blinded until the coordinator's go)"
