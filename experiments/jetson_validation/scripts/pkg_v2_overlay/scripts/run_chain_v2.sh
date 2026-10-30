#!/usr/bin/env bash
# run_chain_v2.sh - the v2 on-device validation sequence, one step after the other (start with run_step.sh run_chain_v2).
# Every step is resumable / skipped when its result exists. Timing first (needs locked clocks: run_timing.sh checks).
#  1 timing_main : 6 methods x 2 seqs x 2 offsets, rate 1.0, back-end v1 (frozen)  + trtbench
#  2 timing_bv2  : back-end v2 (results/backend_v2), openvins / SAVIOR Py + C++ / SAVIOR-edge Py + C++
#  3 pipe_masks + YOLO-level mask agreement (offline)
#  4 accuracy    : closed loop, 6 methods x 2 seqs x 3 offsets, rate 0.5, back-end v1, compare vs desktop
#  5 accuracy_bv2: closed loop, openvins / Y-Cls / SAVIOR / SAVIOR-edge, back-end v2 (compared on the server)
set -uo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; O="$(dirname "${D}")/out"
step() { echo "[chain] $(date '+%F %T') $*"; }
done_t() { [[ -f "${O}/$1/timing.md" ]]; }
if ! done_t timing_main; then step timing_main; SJ_TIMING_NAME=timing_main "${D}/run_timing.sh"; step "timing_main exit $?"; fi
if ! done_t timing_bv2; then step timing_bv2; SJ_BACKEND=v2 SJ_TIMING_NAME=timing_bv2 SJ_TRTBENCH=0 \
    SJ_TIMING_METHODS="openvins sens_fix1 savior_cpp savior_edge savior_edge_cpp" "${D}/run_timing.sh"; step "timing_bv2 exit $?"; fi
step pipe_masks; "${D}/run_pipe_masks.sh"; step "pipe_masks exit $?"
[[ -f "${O}/masks/agreement.json" ]] || { step masks; "${D}/run_accuracy.sh" --masks-only; step "masks exit $?"; }
step accuracy; SJ_METHODS="openvins yolo_naive sens_fix1 savior_edge savior_cpp savior_edge_cpp" "${D}/run_accuracy.sh" --closed-loop-only; step "accuracy exit $?"
step accuracy_bv2; SJ_BACKEND=v2 SJ_ACC_NAME=accuracy_bv2 SJ_METHODS="openvins yolo_naive sens_fix1 savior_edge" "${D}/run_accuracy.sh" --no-compare; step "accuracy_bv2 exit $?"
step "chain done"
