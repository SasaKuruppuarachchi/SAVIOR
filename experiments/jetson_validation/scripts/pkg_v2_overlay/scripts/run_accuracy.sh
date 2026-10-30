#!/usr/bin/env bash
# run_accuracy.sh - accuracy validation on the Jetson against the desktop reference.
#   A. offline mask agreement: Jetson engines vs the desktop FP16 engines on every 10th left frame (both sequences)
#      -> out/masks/agreement.json                                                          (~10 min)
#   B. closed loop: 2 sequences (hall_t1_L3, aisles_t1_L2) x 3 offsets (0.0/0.6/1.2 s = desktop run_01/04/07) x 4 methods
#      (openvins, yolo_naive = Y-Cls, sens_fix1 = SAVIOR, savior_edge = SAVIOR-edge), rate 0.5, deterministic ov_set,
#      mask_policy wait - settings read only from the frozen yamls. One container per method x sequence, one at a time.
#      -> out/accuracy/<seq>/<method>/run_XX                                                (~2.5-3.5 h)
#   C. sync + pose-count check (pkg_sync.py); a run invalid ONLY by mask sync is re-run once at rate 0.25 (tolerances.json)
#   D. savior-eval multi (posyaw, full sequence) + runstats per method dir
#   E. compare vs desktop (ATE tolerances, md5 reported, closed-loop mask stats) -> out/accuracy/compare.{json,txt}
# Resumable: a method x sequence whose 3 runs already exist is skipped (SJ_FORCE=1 re-runs everything).
# Usage: scripts/run_accuracy.sh [--masks-only|--closed-loop-only|--compare-only]
# Env: SJ_RATE (0.5; do not change), SJ_RETRY_RATE (0.25; empty = no retry), SJ_RUN_TIMEOUT (5400 s per run)
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
MODE="${1:-all}"
RATE="${SJ_RATE:-0.5}"; RETRY_RATE="${SJ_RETRY_RATE-0.25}"
PAIRS="1:0.0,4:0.6,7:1.2"
FAKE=(); [[ "${SJ_FAKE_RUNS:-0}" == 1 ]] && FAKE=(--fake)
AN="${SJ_ACC_NAME:-accuracy}"; A="${OUTD}/${AN}"; M="${OUTD}/masks"; mkdir -p "${A}" "${M}"   # v2: SJ_ACC_NAME (e.g. accuracy_bv2 with SJ_BACKEND=v2)
sj_require_image; sj_require_ws; sj_require_idle_pkg
export SJ_INSTALL_MAIN SJ_INSTALL_EDGE SJ_MODEL_S SJ_MODEL_N
PASSENV=(); for v in SJ_INSTALL_MAIN SJ_INSTALL_EDGE SJ_MODEL_S SJ_MODEL_N SJ_RUN_TIMEOUT; do [[ -n "${!v:-}" ]] && PASSENV+=(-e "${v}=${!v}"); done

# ------------------------------------------------------------------------------------------- A. offline mask agreement
masks() {
    [[ "${SJ_DRYRUN:-0}" == 1 ]] || { [[ -f "${MODEL_S}" && -f "${MODEL_N}" ]] || die "engines missing: run scripts/export_engines.sh first"; }
    local cmd="set -e; L=${LIB}; : > ${M}/agreement.jsonl"
    for seq in "${SEQS[@]}"; do
        local bag="${WS}/data/warehouse/ros2_stereoseg/${seq}"
        for e in s n int8_s int8_n; do
            local eng ref info=""
            case "${e}" in
                s) eng="${MODEL_S}"; ref=s ;;
                n) eng="${MODEL_N}"; ref=n ;;
                int8_s) eng="${WS}/models/warehouse/int8/yolo26s-seg-warehouse-int8.engine"; ref=s; info=--informational ;;
                int8_n) eng="${WS}/models/warehouse/int8/yolo26n-seg-warehouse-int8.engine"; ref=n; info=--informational ;;
            esac
            cmd+="; if [ -f ${eng} ]; then python3 \$L/mask_dump.py --bag ${bag} --engine ${eng} --out ${M}/device_${e}_${seq}.npz > ${M}/dump_${e}_${seq}.log 2>&1 && \
python3 \$L/mask_agreement.py --ref ${REF}/desktop_masks/desktop_${ref}_${seq}.npz --test ${M}/device_${e}_${seq}.npz --label ${e}_${seq} \
--tol ${REF}/tolerances.json ${info} >> ${M}/agreement.jsonl || echo 'mask step ${e} ${seq} FAILED'; else echo 'skip ${e} (no engine)'; fi"
        done
    done
    log "accuracy A: offline mask agreement (every 10th frame, s/n FP16 + INT8 if built)"
    sj_docker masks "${cmd}" "${PASSENV[@]}" > "${OUTD}/logs/acc_masks.log" 2>&1 || die "mask agreement step failed (out/logs/acc_masks.log)"
    [[ "${SJ_DRYRUN:-0}" == 1 ]] && return 0
    python3 - "${M}/agreement.jsonl" "${M}/agreement.json" <<'EOF'
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith('{')]
json.dump({'results': rows}, open(sys.argv[2], 'w'), indent=1)
for r in rows:
    print(f"  masks {r['label']:22s} {r['verdict']}{' (informational)' if r['informational'] else ''}: worst class IoU {r['worst_class_iou']}, "
          f"instance recall {r['instances']['recall']} precision {r['instances']['precision']}, predict median {r['predict_ms_median']['test']:.1f} ms "
          f"(desktop {r['predict_ms_median']['ref']:.1f})")
EOF
}

# ------------------------------------------------------------------------------------------- B. closed loop
complete() {  # complete <seq> <method>: 0 if run_01/04/07 all have run_info.yaml
    local r; for r in 01 04 07; do [[ -f "${A}/$1/$2/run_${r}/run_info.yaml" ]] || return 1; done; return 0
}
closed_loop() {
    local seq m dom=101
    for seq in "${SEQS[@]}"; do
        for m in "${METHODS[@]}"; do      # openvins first: its pose counts are the reference of the pose-count rule
            dom=$((dom + 1))
            if [[ "${SJ_FORCE:-0}" != 1 ]] && complete "${seq}" "${m}"; then log "accuracy B: ${seq} ${m} complete, skipping"; continue; fi
            rm -rf "${A:?}/${seq}/${m}"
            log "accuracy B: ${seq} ${m} (3 offsets, rate ${RATE})"
            local t0; t0=$(date +%s)
            SJ_DOMAIN=${dom} sj_docker "acc_${m}_${seq}" "bash ${LIB}/run_one.sh ${seq} ${m} ${AN} ${RATE} ${PAIRS} ${FAKE[*]:-}" "${PASSENV[@]}" \
                > "${OUTD}/logs/${AN}_${seq}_${m}.log" 2>&1 || log "accuracy B: WARNING container exit != 0 for ${seq} ${m} (see log)"
            log "accuracy B: ${seq} ${m} finished in $(( ($(date +%s) - t0) / 60 )) min"
        done
    done
}

sync_and_retry() {
    log "accuracy C: sync + pose-count check"
    sj_py sync "${LIB}/pkg_sync.py" "${A}" --json "${A}/sync.json" | tee "${OUTD}/logs/acc_sync.log" || true
    [[ "${SJ_DRYRUN:-0}" == 1 || -z "${RETRY_RATE}" || ${#FAKE[@]} -gt 0 ]] && return 0
    local retry
    retry="$(python3 -c "
import json; d = json.load(open('${A}/sync.json'))
print(' '.join(f\"{r['seq']}:{r['method']}:{r['run']}\" for r in d['rows'] if r['exit_ok'] and not r['sync_ok'] and r.get('rate') == ${RATE}))")"
    [[ -z "${retry}" ]] && return 0
    log "accuracy C: re-running sync-invalid runs once at rate ${RETRY_RATE}: ${retry}"
    local x seq m run idx off
    for x in ${retry}; do
        IFS=: read -r seq m run <<< "${x}"; idx=$((10#${run#run_}))
        case "${idx}" in 1) off=0.0 ;; 4) off=0.6 ;; 7) off=1.2 ;; *) continue ;; esac
        mkdir -p "${A}/_invalid/${seq}/${m}"; rm -rf "${A}/_invalid/${seq}/${m}/${run}_r${RATE}"
        mv "${A}/${seq}/${m}/${run}" "${A}/_invalid/${seq}/${m}/${run}_r${RATE}"
        SJ_DOMAIN=150 sj_docker "acc_retry_${m}_${seq}" "bash ${LIB}/run_one.sh ${seq} ${m} ${AN} ${RETRY_RATE} ${idx}:${off}" "${PASSENV[@]}" \
            > "${OUTD}/logs/acc_retry_${seq}_${m}_${run}.log" 2>&1 || true
    done
    sj_py sync2 "${LIB}/pkg_sync.py" "${A}" --json "${A}/sync.json" | tee "${OUTD}/logs/acc_sync.log" || true
}

evaluate() {
    log "accuracy D: savior-eval multi + runstats"
    local cmd="set +e"
    for seq in "${SEQS[@]}"; do for m in "${METHODS[@]}"; do
        local d="${A}/${seq}/${m}"
        cmd+="; if [ -d ${d} ]; then savior-eval multi --runs ${d} --gt ${WS}/data/warehouse/gt/${seq}.txt --label ${m} --pattern 'run_[0-9][0-9]' --no-plot > ${d}/eval_multi.log 2>&1 || echo 'eval fail ${d}'; \
savior-eval runstats --runs ${d} --out ${d}/runstats.md > ${d}/runstats.log 2>&1 || echo 'runstats fail ${d}'; fi"
    done; done
    sj_docker eval "${cmd}" "${PASSENV[@]}" | tee "${OUTD}/logs/acc_eval.log"
}

compare() {
    log "accuracy E: compare vs desktop"
    sj_py compare "${LIB}/accuracy_compare.py" "${A}" "${A}" | tee "${OUTD}/logs/acc_compare.log"
}

case "${MODE}" in
    all) masks; closed_loop; sync_and_retry; evaluate; compare ;;
    --masks-only) masks ;;
    --closed-loop-only) closed_loop; sync_and_retry; evaluate; compare ;;
    --compare-only) sync_and_retry; evaluate; compare ;;
    --no-compare) closed_loop; sync_and_retry; evaluate; exit 0 ;;   # v2: e.g. backend v2 (no desktop v1 reference applies)
    *) die "unknown mode ${MODE}" ;;
esac
[[ "${SJ_DRYRUN:-0}" == 1 ]] && exit 0
ov="$(python3 -c "import json; print(json.load(open('${A}/compare.json'))['overall'])" 2>/dev/null || echo FAIL)"
log "accuracy: OVERALL ${ov} -> out/accuracy/compare.txt"
[[ "${ov}" != FAIL ]]
