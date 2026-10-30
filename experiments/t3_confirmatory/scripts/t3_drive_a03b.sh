#!/usr/bin/env bash
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
source <(sed -n '1,/^for ph in/p' $D0/t3_drive.sh | sed '$d' | sed 's#RUNNER=\$D/run_t3_ov2.sh#RUNNER=$D/run_t3_rr.sh#')
type ov_rerun | grep -q 'RUNNER=$D/run_t3_rr.sh' || { echo "ov_rerun substitution failed"; exit 2; }
say "t3_drive_a03 started; waiting for run_t3.sh check ov2 ov2_eval ov2_audit"
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
say "t3_drive_a03b finished (runs + audits only; NO analysis, blinded until the coordinator's go)"
