#!/usr/bin/env bash
# run_chain3_v2.sh [pid-to-wait-for] - replaces run_chain2_v2.sh (written 2026-10-24 23:55):
#  0 accuracy (v1) runs that are sync-valid but INVALID by the pose-count rule only (Python node at rate 0.5: the filter had not
#    caught up when the bag ended) are re-run once at rate 0.25, the same treatment the package gives sync-invalid runs
#    (reference/tolerances.json sync.retry); then sync + eval + compare again (run_accuracy.sh --compare-only)
#  1 timing_rep   : frozen protocol, OpenVINS / C++ main / C++ edge, 2 MORE offsets (1.2, 1.8 s) per sequence (start-up drop repeatability)
#  2 timing_deploy: DIAGNOSTIC (not the frozen protocol): mask_timeout_ms 100 instead of 30000, Python + C++ main / edge
#  3 accuracy_bv2 : back-end v2, OpenVINS + SAVIOR (C++) + SAVIOR-edge (C++), rate 0.5, 3 offsets
set -uo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; O="$(dirname "${D}")/out"
# shellcheck source=common.sh
source "${D}/common.sh"
step() { echo "[chain3] $(date '+%F %T') $*"; }
if [[ -n "${1:-}" ]]; then step "waiting for pid $1"; while kill -0 "$1" 2>/dev/null; do sleep 20; done; fi
A="${OUTD}/accuracy"
retry="$(python3 -c "
import json; d = json.load(open('${A}/sync.json'))
print(' '.join(f\"{r['seq']}:{r['method']}:{r['run']}\" for r in d['rows'] if r['exit_ok'] and r['sync_ok'] and not r['pose_ok'] and r.get('rate') == 0.5))")"
step "pose-only invalid runs re-run at 0.25: ${retry:-none}"
for x in ${retry}; do
    IFS=: read -r seq m run <<< "${x}"; idx=$((10#${run#run_}))
    case "${idx}" in 1) off=0.0 ;; 4) off=0.6 ;; 7) off=1.2 ;; *) continue ;; esac
    mkdir -p "${A}/_invalid/${seq}/${m}"; rm -rf "${A}/_invalid/${seq}/${m}/${run}_r0.5"
    mv "${A}/${seq}/${m}/${run}" "${A}/_invalid/${seq}/${m}/${run}_r0.5"
    SJ_DOMAIN=151 sj_docker "acc_retry2_${m}_${seq}" "bash ${LIB}/run_one.sh ${seq} ${m} accuracy 0.25 ${idx}:${off}" \
        > "${OUTD}/logs/acc_retry2_${seq}_${m}_${run}.log" 2>&1 || true
done
step "accuracy compare"; SJ_RETRY_RATE= SJ_METHODS="openvins yolo_naive sens_fix1 savior_edge savior_cpp savior_edge_cpp" "${D}/run_accuracy.sh" --compare-only; step "compare exit $?"
if [[ ! -f "${O}/timing_rep/timing.md" ]]; then step timing_rep; SJ_TIMING_NAME=timing_rep SJ_TRTBENCH=0 SJ_TIMING_PAIRS=3:1.2,4:1.8 \
    SJ_TIMING_METHODS="openvins savior_cpp savior_edge_cpp" "${D}/run_timing.sh"; step "timing_rep exit $?"; fi
if [[ ! -f "${O}/timing_deploy/timing.md" ]]; then step timing_deploy; SJ_TIMING_NAME=timing_deploy SJ_TRTBENCH=0 SJ_MASK_TIMEOUT_MS=100 \
    SJ_TIMING_METHODS="sens_fix1 savior_cpp savior_edge savior_edge_cpp" "${D}/run_timing.sh"; step "timing_deploy exit $?"; fi
step accuracy_bv2; SJ_BACKEND=v2 SJ_ACC_NAME=accuracy_bv2 SJ_METHODS="openvins savior_cpp savior_edge_cpp" "${D}/run_accuracy.sh" --no-compare; step "accuracy_bv2 exit $?"
step "chain3 done"
