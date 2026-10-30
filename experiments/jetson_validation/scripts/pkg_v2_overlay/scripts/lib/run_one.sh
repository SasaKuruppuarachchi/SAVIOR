#!/usr/bin/env bash
# run_one.sh <seq> <method> <dsn> <rate> <idx:offset[,idx:offset...]> [--ovtime] [--mem] [--fake]
# Runs INSIDE the image. One method x sequence, offsets in series, exactly the desktop savior-run protocol
# (results/p7/scripts/run_method.sh / results/m2b_heldout/scripts/run_m2b.sh): settings from the frozen yamls (pkg_args.py),
# mask_policy wait, mask_timeout_ms 30000, feature_stats auto, cooldown 1 s, deterministic ov_set.
# -> $OUTD/<dsn>/<seq>/<method>/run_XX (XX = idx, so run_01/04/07 = offsets 0.0/0.6/1.2 s like the desktop runs).
#   --ovtime  OpenVINS per-update timing file (record_timing_information; no effect on the estimate) -> run_XX/ov_timing.txt
#   --mem     per-process memory sampler (VmRSS / VmHWM every 0.5 s) -> run_XX/mem.csv
#   --lat     (v2) latency probe (latprobe.py: receive times of /cam0/image_raw, /savior/mask/left, /ov_msckf/poseimu) -> run_XX/lat.csv
#   --fake    x86 logic test: copy the desktop reference run instead of running anything
set -euo pipefail
SEQ=$1; METHOD=$2; DSN=$3; RATE=$4; PAIRS=$5; shift 5
OVTIME=0; MEM=0; FAKE=0; LAT=0
for a in "$@"; do case "$a" in --ovtime) OVTIME=1 ;; --mem) MEM=1 ;; --lat) LAT=1 ;; --fake) FAKE=1 ;; *) echo "bad option $a"; exit 2 ;; esac; done
LIB="${PKG_ROOT}/scripts/lib"; OUTD="${PKG_ROOT}/out"
mapfile -t L < <(python3 "${LIB}/pkg_args.py" "${SEQ}" "${METHOD}")
[[ ${#L[@]} -ge 8 ]] || { echo "pkg_args.py failed"; exit 2; }
INSTALL=${L[0]}; LAUNCH=${L[1]}; CFG=${L[2]}; BAG=${L[3]}; OVSET=${L[5]}; TOPICS=${L[6]}; PSET=${L[7]}
ARGS=("${L[@]:8}")
INSTALL_MAIN="${SJ_INSTALL_MAIN:-${SAVIOR_WS}/install}"
set +u
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
[[ "${FAKE}" == 1 ]] || source "${INSTALL_MAIN}/setup.bash"
# v2: INSTALL = <install>[+<cpp overlay>]; the cpp overlay (built on top of the main install) is sourced with local_setup.bash
INST1=${INSTALL%%+*}; INST2=""; [[ "${INSTALL}" == *+* ]] && INST2=${INSTALL#*+}
[[ "${FAKE}" == 1 || "${INST1}" == "${INSTALL_MAIN}" ]] || source "${INST1}/setup.bash"   # edge overlay on top (as on the desktop)
[[ "${FAKE}" == 1 || -z "${INST2}" ]] || source "${INST2}/local_setup.bash"            # C++ node overlay (results/cpp_port protocol)
set -u
[[ "${OVTIME}" == 1 ]] && OVSET="${OVSET} record_timing_information=true record_timing_filepath=/tmp/ov_timing.txt"
LA=(--launch-arg "rate:=${RATE}" --launch-arg feature_stats:=auto --launch-arg "ov_set:=${OVSET}" --launch-arg "topics:=${TOPICS}")
if [[ "${LAUNCH}" == savior.launch.py ]]; then
    # v2: SJ_MASK_TIMEOUT_MS = deployment-style wait timeout (the frozen protocol value 30000 ms is an offline-replay
    # setting: a single frame dropped by a too-slow perception node then stalls the filter for 30 s)
    LA+=(--launch-arg mask_policy:=wait --launch-arg "mask_timeout_ms:=${SJ_MASK_TIMEOUT_MS:-30000}")
    [[ -n "${PSET// }" ]] && LA+=(--launch-arg "pset:=${PSET}")
fi
for a in "${ARGS[@]}"; do LA+=(--launch-arg "${a}"); done
RD="${OUTD}/${DSN}/${SEQ}/${METHOD}"
mkdir -p "${RD}"
printf '%s\n' "INSTALL=${INSTALL}" "LAUNCH=${LAUNCH}" "CFG=${CFG}" "BAG=${BAG}" "OVSET=${OVSET}" "TOPICS=${TOPICS}" "PSET=${PSET}" \
    "ARGS=${ARGS[*]:-}" "PAIRS=${PAIRS}" "RATE=${RATE}" "HOST=$(hostname)" "DATE=$(date -Is)" >> "${RD}/pkg_settings.txt"
for pair in ${PAIRS//,/ }; do
    i=${pair%%:*}; off=${pair#*:}
    R="${RD}/run_$(printf %02d "${i}")"
    mkdir -p "${R}"
    echo "[run_one] $(date +%T) ${SEQ} ${METHOD} run_$(printf %02d "${i}") offset ${off} rate ${RATE}"
    if [[ "${FAKE}" == 1 ]]; then
        cp -r "${PKG_ROOT}/reference/desktop_runs/${SEQ}/${METHOD}/run_$(printf %02d "${i}")/." "${R}/"
        echo "FAKE run (copied from the desktop reference)" > "${R}/FAKE"
        [[ -f "${R}/run_info.yaml" ]] && sed -i "s/^status: .*/status: ok/" "${R}/run_info.yaml"
        continue
    fi
    SP=""
    if [[ "${MEM}" == 1 ]]; then python3 "${LIB}/memsampler.py" --out "${R}/mem.csv" & SP=$!; fi
    LP=""
    if [[ "${LAT}" == 1 ]]; then python3 "${LIB}/latprobe.py" --out "${R}/lat.csv" > "${R}/latprobe.log" 2>&1 & LP=$!; sleep 2; fi
    date +%s.%N > "${R}/t_start"
    savior-run --launch-pkg savior_bringup --launch-file "${LAUNCH}" --bag "${BAG}" --config "${CFG}" -n 1 --start-index "${i}" \
        --results-root "${OUTD}" --dataset "${DSN}" --seq "${SEQ}" --method "${METHOD}" --rate "${RATE}" \
        --domain-id "${ROS_DOMAIN_ID}" --cooldown 1 --timeout "${SJ_RUN_TIMEOUT:-5400}" \
        --launch-arg "start_offset:=${off}" "${LA[@]}" || echo "[run_one] run ${i} failed"
    date +%s.%N > "${R}/t_end"
    [[ -n "${SP}" ]] && { kill "${SP}" 2>/dev/null || true; wait "${SP}" 2>/dev/null || true; }
    [[ -n "${LP}" ]] && { kill -INT "${LP}" 2>/dev/null || true; wait "${LP}" 2>/dev/null || true; [[ -f "${R}/lat.csv" ]] && gzip -f "${R}/lat.csv"; }
    [[ -f "${R}/savior_stats.jsonl" ]] && gzip -f "${R}/savior_stats.jsonl"
    [[ -f "${R}/launch.log" ]] && gzip -f "${R}/launch.log"
    [[ -f /tmp/ov_timing.txt ]] && mv /tmp/ov_timing.txt "${R}/ov_timing.txt"
done
exit 0
