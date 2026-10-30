#!/usr/bin/env bash
# run_timing.sh - timing on the Jetson: rate 1.0 (20 Hz stereo, real time), ONE container for everything, nothing else of
# ours running. Methods: openvins (OpenVINS alone, no perception node), yolo_naive, sens_fix1 (SAVIOR), savior_edge;
# sequences hall_t1_L3 + aisles_t1_L2; offsets 0.0 / 0.6 s (SJ_TIMING_PAIRS); OpenVINS per-update timing
# (record_timing_information, no effect on the estimate); per-stage savior_node timings (savior_stats); per-process peak
# memory (memsampler, /proc VmHWM); tegrastats on the host (CPU / GPU GR3D / EMC load, RAM, swap, temperatures, VDD_IN power).
# The POWER MODE is recorded before and after and NEVER changed. If it is not MAXN the script stops (exit 10) so the user can
# decide: keep it (rerun with SJ_ACCEPT_POWER_MODE=1) or switch it themselves (e.g. sudo nvpmodel -m 0; sudo jetson_clocks).
# Other (non-saviorsj) containers running -> stop (exit 11) so the user can decide (SJ_ACCEPT_OTHERS=1 to measure anyway).
# Outputs: out/timing/{timing.json,timing.md,resources.json,tegrastats.log,trtbench.jsonl,power_*.json,markers.txt,sync.json}
# Time: ~45-60 min.   Usage: scripts/run_timing.sh [--parse-only]
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
TN="${SJ_TIMING_NAME:-timing}"; T="${OUTD}/${TN}"; mkdir -p "${T}"   # v2: SJ_TIMING_NAME = out/<name> (sessions never overwrite each other)
PAIRS="${SJ_TIMING_PAIRS:-1:0.0,2:0.6}"
FAKE=""; [[ "${SJ_FAKE_RUNS:-0}" == 1 ]] && FAKE=--fake
PASSENV=(); for v in SJ_INSTALL_MAIN SJ_INSTALL_EDGE SJ_MODEL_S SJ_MODEL_N SJ_RUN_TIMEOUT SJ_TIMING_METHODS SJ_TIMING_SEQS SJ_TRTBENCH SJ_TIMING_NAME SJ_MASK_TIMEOUT_MS SJ_IDLE_S; do [[ -n "${!v:-}" ]] && PASSENV+=(-e "${v}=${!v}"); done

parse() {
    log "timing: parsing"
    sj_py tparse "${LIB}/timing_parse.py" "${T}" > "${OUTD}/logs/${TN}_parse.log" 2>&1 || die "timing_parse failed (out/logs/timing_parse.log)"
    sj_py tsync "${LIB}/pkg_sync.py" "${T}" --json "${T}/sync.json" --timing > "${OUTD}/logs/${TN}_sync.log" 2>&1 || true
    cat "${T}/timing.md"
    tail -1 "${OUTD}/logs/${TN}_sync.log"
}
if [[ "${1:-}" == --parse-only ]]; then parse; exit 0; fi

sj_require_image; sj_require_ws; sj_require_idle_pkg
[[ -n "${FAKE}" || "${SJ_DRYRUN:-0}" == 1 ]] || { [[ -f "${MODEL_S}" && -f "${MODEL_N}" ]] || die "engines missing: run scripts/export_engines.sh first"; }

bash "${LIB}/power_state.sh" "${T}/power_before.json"
pm="$(python3 -c "import json; print(json.load(open('${T}/power_before.json'))['power_mode'])")"
if [[ "${pm}" != *MAXN* && "${SJ_ACCEPT_POWER_MODE:-0}" != 1 && "${SJ_ARCH}" == arm64 ]]; then
    echo "STOP: power mode is '${pm}', not MAXN. Ask the user: (a) measure in this mode -> SJ_ACCEPT_POWER_MODE=1 scripts/run_timing.sh"
    echo "      or (b) the user switches it (system change, e.g. 'sudo nvpmodel -m 0' [+ 'sudo jetson_clocks']) and you rerun."
    exit 10
fi
# v2: locked clocks required (jetson_clocks: GPU devfreq min == max); SJ_ACCEPT_UNLOCKED=1 measures anyway (recorded)
lk="$(python3 -c "import json; print(json.load(open('${T}/power_before.json'))['jetson_clocks_inferred'])")"
if [[ "${lk}" != on && "${SJ_ACCEPT_UNLOCKED:-0}" != 1 && "${SJ_ARCH}" == arm64 ]]; then
    echo "STOP: clocks are not locked (jetson_clocks_inferred=${lk}); the author must run 'sudo jetson_clocks' (or SJ_ACCEPT_UNLOCKED=1)."
    exit 12
fi
others="$(docker ps --format '{{.Names}}' | grep -v "^${SJ_PREFIX}_" | tr '\n' ' ' || true)"
if [[ -n "${others// }" && "${SJ_ACCEPT_OTHERS:-0}" != 1 ]]; then
    echo "STOP: other containers are running (${others}). They disturb timing but are NOT ours: never stop them."
    echo "      Ask the user whether to pause them, or measure anyway with SJ_ACCEPT_OTHERS=1 (recorded in power_before.json)."
    exit 11
fi
rm -rf "${T:?}"/*_t1_* "${T}/markers.txt" "${T}/tegrastats.log"

TGP=""
if command -v tegrastats >/dev/null && [[ "${SJ_DRYRUN:-0}" != 1 ]]; then
    # own session/process group so that exactly this tegrastats (and its reader) is stopped at the end (never 'tegrastats --stop',
    # which would also stop someone else's instance)
    rm -f "${T}/tegrastats.pgid"
    LC_ALL=C setsid bash -c 'echo $$ > "$0"; tegrastats --interval 200 | while IFS= read -r l; do printf "%s %s\n" "${EPOCHREALTIME}" "${l}"; done' \
        "${T}/tegrastats.pgid" > "${T}/tegrastats.log" 2>&1 &
    for _ in 1 2 3 4 5 6 7 8 9 10; do [[ -s "${T}/tegrastats.pgid" ]] && break; sleep 0.2; done
    TGP="$(cat "${T}/tegrastats.pgid" 2>/dev/null || true)"
    log "timing: tegrastats recording (pgid ${TGP})"
else
    log "timing: tegrastats not available - only /proc memory + savior/ov timings are recorded"
fi
cleanup() { [[ -n "${TGP}" ]] && kill -TERM -- "-${TGP}" 2>/dev/null || true; }
trap cleanup EXIT

log "timing: one container, rate 1.0, pairs ${PAIRS}, power mode '${pm}'"
t0=$(date +%s)
SJ_DOMAIN=200 sj_docker timing "bash ${LIB}/timing_driver.sh ${PAIRS} ${FAKE}" "${PASSENV[@]}" > "${OUTD}/logs/${TN}_runs.log" 2>&1 \
    || log "timing: WARNING container exit != 0 (see out/logs/timing_runs.log)"
log "timing: runs finished in $(( ($(date +%s) - t0) / 60 )) min"
cleanup; TGP=""
bash "${LIB}/power_state.sh" "${T}/power_after.json"
[[ "${SJ_DRYRUN:-0}" == 1 ]] && exit 0
parse
log "timing: done -> out/timing/timing.md"
