#!/usr/bin/env bash
# t3_run_analysis_vins.sh : = t3_run_analysis_ov2.sh (ANALYSIS_OV2.md5) with ONE change per AMENDMENT_09: vins_runs is visible (complete, 3360/3360 valid); dyna_masks_runs stays hidden.
# t3_run_analysis_ov2.sh : = t3_run_analysis.sh (md5 in ANALYSIS_PREP.md5, UNCHANGED) with ONE change per coordinator GO (AMENDMENT_08): the analysis container sees an EMPTY read-only directory over results/t3_confirmatory/vins_runs and dyna_masks_runs, so the frozen stats_t3.py / t3_extras.py / t3_amend0x.py / t3_strict_sens.py load no VINS-family or DynaVINS+masks data (VINS-family comparisons drop out: not computed on a partial set). No frozen file is edited.
# t3_run_analysis.sh : PREPARED, run ONLY after the coordinator's go (blinding). Runs the t3 analysis under the AMENDMENT_05 rule
# without editing the frozen stats_t3.py:
#   1. clarified invalid list  tables/invalid_clarified.txt = (m2bsync tables/invalid.txt  minus  runs that are tail-only in
#      tables/frames_tail_only.txt AND sync_ok in tables/sync_audit.csv)  union  frames-audit clarified invalid (tables/frames_invalid.txt,
#      OV family lines only, as 'seq method run'). m2bsync's raw tables/invalid.txt is kept unchanged alongside.
#   2. stats_t3.py (frozen; it hard-codes tables/invalid.txt) runs with tables/invalid_clarified.txt bind-mounted read-only OVER
#      tables/invalid.txt inside its container, so it reads the clarified list; on the host invalid.txt stays the raw m2bsync file.
#      (stats_t3 uses the list for reporting only; it never drops runs. No run is dropped under either rule.)
#   3. t3_extras.py, t3_amend03.py, t3_amend04.py, t3_strict_sens.py (strict-complete view), same image.
# Requires the final audits of t3_drive_a06.sh (tables/frames_audit.csv over all roots, sync_audit.csv, invalid.txt).
set -euo pipefail
[[ ${T3_ANALYSIS_GO:-} == yes ]] || { echo "refusing: blinded; set T3_ANALYSIS_GO=yes only after the coordinator's go"; exit 3; }
WS=/home/sasa/workspace/savior_ws; T=$WS/results/t3_confirmatory; D=$T/scripts; TB=$T/tables
(cd $T && md5sum -c --status DESIGN.md5) || { echo "refusing: DESIGN.yaml md5"; exit 3; }
python3 - $TB/invalid.txt $TB/sync_audit.csv $TB/frames_tail_only.txt $TB/frames_invalid.txt $TB/invalid_clarified.txt <<'PY'
import csv, sys
inv, sync, tail, fr, out = sys.argv[1:]
key = lambda l: tuple(l.split()[-3:])  # noqa: E731
m2b = {key(l) for l in open(inv) if l.strip()}
ok_sync = {(r['seq'], r['method'], r['run']) for r in csv.DictReader(open(sync)) if r['sync_ok'] == '1'}
tl = {key(l) for l in open(tail) if l.strip() and l.split()[0] == 'ov'}
frv = {key(l) for l in open(fr) if l.strip() and l.split()[0] == 'ov'}
sel = sorted((m2b - {k for k in m2b if k in tl and k in ok_sync}) | frv)
open(out, 'w').write(''.join(' '.join(k) + '\n' for k in sel))
print(f'm2bsync raw invalid {len(m2b)}; tail-only+sync-ok removed {len(m2b & tl & ok_sync)}; frames clarified-invalid {len(frv)}; clarified invalid {len(sel)}')
PY
RUN="docker run --rm --network none -v /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/empty_ro:$T/dyna_masks_runs:ro --user $(id -u):$(id -g) -v $WS:$WS -e MPLCONFIGDIR=/tmp"
$RUN -v $TB/invalid_clarified.txt:$TB/invalid.txt:ro --name t3stats_$$ savior:humble-cuda12.8 python3 -I $D/stats_t3.py
for s in t3_extras.py t3_amend03.py t3_amend04.py t3_strict_sens.py; do
  $RUN --name t3an_${s%.py}_$$ savior:humble-cuda12.8 python3 -I $D/$s > $TB/${s%.py}.log 2>&1 || echo "$s failed"
done
echo "tables -> $TB (primary.md secondary.md failures.md cap_sensitivity.md per_environment.md controls.md failure_diff.md nonfailed.md dyna_masks.md amend03.md amend04.md strict_sensitivity.md)"
