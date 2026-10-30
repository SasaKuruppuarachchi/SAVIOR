#!/usr/bin/env bash
# run_chain2_v2.sh [pid-to-wait-for] - second half of the v2 sequence (written 2026-10-24 22:10, after timing_main showed that the
# Python nodes cannot keep up and that one dropped frame stalls the frozen 30 s wait policy):
#  1 accuracy_bv2 : back-end v2, OpenVINS + SAVIOR (C++) + SAVIOR-edge (C++) (C++ node = md5-identical to the Python node on the
#                   desktop; the Python nodes are not sync-valid at rate 0.5 on the device), rate 0.5, 3 offsets
#  2 timing_rep   : frozen protocol, C++ main / edge, 2 MORE offsets (1.2, 1.8 s) per sequence: repeatability of the start-up drop
#  3 timing_deploy: DIAGNOSTIC (not the frozen protocol): mask_timeout_ms 100 instead of 30000, Python + C++ main / edge, offsets 0.0/0.6
set -uo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; O="$(dirname "${D}")/out"
step() { echo "[chain2] $(date '+%F %T') $*"; }
if [[ -n "${1:-}" ]]; then step "waiting for pid $1"; while kill -0 "$1" 2>/dev/null; do sleep 20; done; fi
step accuracy_bv2; SJ_BACKEND=v2 SJ_ACC_NAME=accuracy_bv2 SJ_METHODS="openvins savior_cpp savior_edge_cpp" "${D}/run_accuracy.sh" --no-compare; step "accuracy_bv2 exit $?"
if [[ ! -f "${O}/timing_rep/timing.md" ]]; then step timing_rep; SJ_TIMING_NAME=timing_rep SJ_TRTBENCH=0 SJ_TIMING_PAIRS=3:1.2,4:1.8 \
    SJ_TIMING_METHODS="openvins savior_cpp savior_edge_cpp" "${D}/run_timing.sh"; step "timing_rep exit $?"; fi
if [[ ! -f "${O}/timing_deploy/timing.md" ]]; then step timing_deploy; SJ_TIMING_NAME=timing_deploy SJ_TRTBENCH=0 SJ_MASK_TIMEOUT_MS=100 \
    SJ_TIMING_METHODS="sens_fix1 savior_cpp savior_edge savior_edge_cpp" "${D}/run_timing.sh"; step "timing_deploy exit $?"; fi
step "chain2 done"
