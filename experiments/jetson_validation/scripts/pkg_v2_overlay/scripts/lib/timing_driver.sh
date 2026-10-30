#!/usr/bin/env bash
# timing_driver.sh <pairs> [--fake] : runs INSIDE the single timing container (run_timing.sh). In order:
#   1. TensorRT micro-benchmark of the device engines (trtbench.py: pure GPU ms per inference)
#   2. for seq in hall_t1_L3 aisles_t1_L2, for method in openvins yolo_naive sens_fix1 savior_edge:
#      run_one.sh <seq> <method> timing 1.0 <pairs> --ovtime --mem   (sequential, nothing else running)
set -uo pipefail
PAIRS="$1"; shift
FAKE=""; [[ "${1:-}" == --fake ]] && FAKE=--fake
LIB="${PKG_ROOT}/scripts/lib"; TN="${SJ_TIMING_NAME:-timing}"; T="${PKG_ROOT}/out/${TN}"
W="${SAVIOR_WS}"
engs=()
for e in "${SJ_MODEL_S:-${W}/models/warehouse/yolo26s-seg-warehouse.engine}" "${SJ_MODEL_N:-${W}/frozen_edge/models/yolo26n-seg-warehouse-672.engine}" \
         "${W}/models/warehouse/int8/yolo26s-seg-warehouse-int8.engine" "${W}/models/warehouse/int8/yolo26n-seg-warehouse-int8.engine"; do
    [[ -f "${e}" ]] && engs+=("${e}")
done
# v2: 30 s idle baseline (tegrastats window idle_start..idle_end: idle power / RAM of the device with this container up)
echo "$(date +%s.%N) idle_start" >> "${T}/markers.txt"; sleep "${SJ_IDLE_S:-30}"; echo "$(date +%s.%N) idle_end" >> "${T}/markers.txt"
echo "[timing] $(date +%T) trtbench on ${#engs[@]} engines"
echo "$(date +%s.%N) trtbench_start" >> "${T}/markers.txt"
if [[ -z "${FAKE}" && ${#engs[@]} -gt 0 && "${SJ_TRTBENCH:-1}" == 1 ]]; then python3 "${LIB}/trtbench.py" "${engs[@]}" > "${T}/trtbench.jsonl" 2> "${T}/trtbench.log" || echo "[timing] trtbench failed"; fi
echo "$(date +%s.%N) trtbench_end" >> "${T}/markers.txt"
# v2: SJ_TIMING_METHODS / SJ_TIMING_SEQS (default: + the C++ node for main and edge), SJ_TRTBENCH=0 skips step 1,
# latency probe (--lat) in every run
for seq in ${SJ_TIMING_SEQS:-hall_t1_L3 aisles_t1_L2}; do
    for m in ${SJ_TIMING_METHODS:-openvins yolo_naive sens_fix1 savior_cpp savior_edge savior_edge_cpp}; do
        echo "$(date +%s.%N) start ${seq} ${m} load $(cut -d' ' -f1 /proc/loadavg)" >> "${T}/markers.txt"
        bash "${LIB}/run_one.sh" "${seq}" "${m}" "${TN}" 1.0 "${PAIRS}" --ovtime --mem --lat ${FAKE} || echo "[timing] ${seq} ${m} failed"
        echo "$(date +%s.%N) end ${seq} ${m} load $(cut -d' ' -f1 /proc/loadavg)" >> "${T}/markers.txt"
        sleep 5   # let clocks / temperatures settle a little between methods
    done
done
echo "[timing] $(date +%T) done"
