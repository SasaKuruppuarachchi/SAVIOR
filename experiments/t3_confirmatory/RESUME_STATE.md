# t3 evaluation: resume state (2026-10-27 20:17, blinded: no outcome has been analysed or looked at)

## Running unattended (setsid/nohup; leave them alone)
| PID | process | does on its own |
|---|---|---|
| 2595215 | `run_t3.sh check ov2 ov2_eval ov2_audit` (started 06:54 by t3_drive.sh) | finishes the planned OV2 queue, then ov2_eval (eval_bv2) and ov2_audit (m2bsync), then exits |
| 2596585 | `bv2queue.py runs_jobs.txt 12` (child of the above) | planned OV2 queue: **521 / 672 jobs** (x 5 runs) done at 20:16, 12 `t3ov_*` containers, 0 non-zero exits |
| 4015306 | `scripts/t3_drive_a05.sh` (current driver; md5 in AMENDMENT_05_IMPL.md5) | waits until PID 2595215 exits, then runs everything below in order, with **no analysis** |

t3_drive_a05.sh order after the planned queue:
1. AMENDMENT_03 queue: 192 jobs / 960 runs (sf1_chibest, ovchi_best) via run_t3_rr.sh, then eval.
2. AMENDMENT_04 queue: 288 jobs / 1440 runs (sf1_nis, savior_sg, ov_nis) via run_t3_sg.sh, then eval.
3. OV-family audits: m2bsync + frames audit (AMENDMENT_05 clarified rule). Re-runs happen unchanged, at most 3 attempts. Tail-only runs are not re-run.
4. `run_t3.sh vins` and `vins_eval`, running alongside the DynaVINS+masks runs (dm_all → results/t3_confirmatory/dyna_masks_runs).
5. VINS and DynaVINS frames audit with re-runs (bag_rerun vins / dyna).
6. Final m2bsync and frames audit over all roots (tables/frames_audit.csv). It then stops. It never runs analyze, stats_t3, t3_extras, t3_amend03/04 or t3_strict_sens.

Every step logs to `/tmp/claude-1002/-home-sasa-workspace-savior-ws/t3_eval/drive.log`. Run logs are under `.../t3_eval/logs/`. Queue logs are under
`/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/bv2/logs/queue_t3*.log`.
Container cap: ≤ 12 t3 containers in total (bv2queue GLOBAL_MAX on t3ov_*, PAR_VINS 3, DynaVINS+masks gated at ncont < 12, ndm ≤ 6).

## Validity so far (interim, scratch-only audit at 18:10)
- 2257 OV runs checked: 2245 clarified-valid (2108 strict, 137 tail only). The 12 invalid were runs still in progress, and there was no mid-sequence frame loss.
- The frames audit passes the t2 held-out smoke check (2760/2760 strict). Disk: NVMe 259 GB free.

## Progress check
```
tail -5 /tmp/claude-1002/-home-sasa-workspace-savior-ws/t3_eval/drive.log
grep -c ' done ' /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/bv2/logs/queue_t3{,_a03,_a04}.log
pgrep -af 'scripts/t3_drive|run_t3.sh'
```

## Resume, if the driver died
Everything can be restarted. bv2queue skips run dirs that already have a trajectory. dm_all skips sequences with a `.done` marker. vins_seq skips mask exports that have `export_done`.
- If PID 2595215 is still alive, or the OV2 queue is complete: `cd /home/sasa/workspace/savior_ws && setsid nohup results/t3_confirmatory/scripts/t3_drive_a05.sh > /tmp/claude-1002/-home-sasa-workspace-savior-ws/t3_eval/drive_a05.out 2>&1 < /dev/null &`
- If the planned OV2 queue itself died before finishing, first run `CONFIRM_T3=yes results/t3_confirmatory/scripts/run_t3.sh ov2 ov2_eval ov2_audit` (resumes the missing jobs), then start t3_drive_a05.sh as above.
- A run in progress when the process was killed leaves a partial run dir. The re-run step catches it, as either missing or invalid.
- Before restarting, check that no stale `t3ov_*`, `sota_*_t3_L*` or `dm_*_t3_L*` containers are left (`docker ps`). Never touch the agipix, velobins, rr_* or rw_* containers.

## Analysis: on hold until the coordinator's go
After the go, run these:
`CONFIRM_T3=yes results/t3_confirmatory/scripts/run_t3.sh analyze`. Then, in the savior image: `python3 -I results/t3_confirmatory/scripts/t3_extras.py`, `t3_amend03.py`, `t3_amend04.py`, `t3_strict_sens.py`. The docker command form is in t3_drive.sh, phase analyze.

## Remaining cleanup (after everything finishes)
- Scratch ROS 1 bags: `.../t3_eval/bags`, `.../t3_eval/dm_bags`. The driver deletes them per sequence, so check that they are empty.
- Moved invalid run dirs: `.../t3_eval/invalid_attempts` (keep until reported).
- Keep NVMe free space above 80 GB. If it drops below, archive run outputs to /home/hdd/sasa/archive/savior/ with a symlink and a row in ARCHIVE_MANIFEST.tsv.

## PAUSED by the coordinator on the author's request (2026-10-29 ~07:50)
- Killed all t3_drive_a07.sh processes and stopped all t3 containers (t3exp_*, sota_*_t3_*, dm_*_t3_*). The agent was stopped. Nothing t3 is running.
- At the pause: OV2 family complete (5760/5760 valid). VINS family: 294/672 method dirs exist, including partial ones. DynaVINS+masks: 42/96 sequences .done.
- Interrupted sequences have no .done marker and are redone on resume (run_method.sh / dm_run remove the run dirs first; mask exports without export_done are redone).
- On resume: first fix the ros1_bag container-name clash ($$ -> $BASHPID or a unique suffix), as a new driver with its md5 recorded. Then restart with the AMENDMENT_07 cap (<= 20 containers, PAR_VINS ~11, PAR_DM ~8). Then the frames audit + completeness check, re-runs, and the analysis only after the coordinator's go (blinded).
- 2026-10-30 13:25 (coordinator): t3_drive_a08 finished. VINS 3360/3360 pass the clarified frame rule. Its final combined audit call (faudit "" ...) failed on an argparse error (unquoted empty --tag); re-run by hand with the same script and arguments and the default empty tag (log: t3_eval/faudit_final.log). No other change. Next: frozen VINS-family secondary analysis (C1-C8, C14).
