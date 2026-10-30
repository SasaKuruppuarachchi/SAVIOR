# shellcheck shell=bash
# common.sh - shared settings of the SAVIOR Jetson validation package (sourced, never executed).
#
# Layout (everything stays inside the package directory, e.g. ~/savior_jetson/savior_jetson_pkg_v1):
#   ws/       colcon workspace = SAVIOR_WS (frozen sources, models, data subset); mounted into containers at the SAME path
#   out/      everything the scripts write (logs, json, runs, engines info); collect_results.sh bundles it
#   reference/ desktop reference numbers (read-only)
#
# Environment overrides (defaults are what the Jetson run should use; the overrides exist for the x86 dry run):
#   SJ_IMAGE        image tag                         default savior:humble-jp6 (arm64) / savior:humble-cuda12.8 (x86)
#   SJ_GPU          auto | runtime | cdi | gpus | none  default: out/gpu_mode.txt (written by build_image.sh), else auto
#   SJ_DRYRUN=1     print every docker command instead of running it
#   SJ_FAKE_RUNS=1  (x86 logic test only) closed-loop runs are NOT executed; desktop reference runs are copied instead
#   SJ_INSTALL_MAIN / SJ_INSTALL_EDGE / SJ_MODEL_S / SJ_MODEL_N / SJ_EXTRA_MOUNTS   (x86 smoke test only)

PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
WS="${PKG_ROOT}/ws"
OUTD="${PKG_ROOT}/out"
REF="${PKG_ROOT}/reference"
LIB="${PKG_ROOT}/scripts/lib"
SJ_PREFIX="saviorsj"            # every container this package starts is named saviorsj_* ; nothing else is ever touched
SEQS=(hall_t1_L3 aisles_t1_L2)
METHODS=(${SJ_METHODS:-openvins yolo_naive sens_fix1 savior_edge})   # v2: SJ_METHODS (e.g. + savior_cpp savior_edge_cpp)

case "$(uname -m)" in
    aarch64 | arm64) SJ_ARCH=arm64; _img=savior:humble-jp6 ;;
    x86_64 | amd64) SJ_ARCH=amd64; _img=savior:humble-cuda12.8 ;;
    *) echo "unsupported arch $(uname -m)" >&2; exit 1 ;;
esac
SJ_IMAGE="${SJ_IMAGE:-${_img}}"

INSTALL_MAIN="${SJ_INSTALL_MAIN:-${WS}/install}"
INSTALL_EDGE="${SJ_INSTALL_EDGE:-${WS}/frozen_edge/install}"
MODEL_S="${SJ_MODEL_S:-${WS}/models/warehouse/yolo26s-seg-warehouse.engine}"
MODEL_N="${SJ_MODEL_N:-${WS}/frozen_edge/models/yolo26n-seg-warehouse-672.engine}"
mkdir -p "${OUTD}/logs"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(ts)] $*" | tee -a "${OUTD}/logs/steps.log" >&2; }
die() { echo "[$(ts)] FATAL: $*" | tee -a "${OUTD}/logs/steps.log" >&2; echo "STOP: ask the user before doing anything else." >&2; exit 1; }
pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; }

# GPU arguments for docker run. Order of preference: explicit SJ_GPU, the mode probed by build_image.sh, auto.
sj_gpu_args() {
    local g="${SJ_GPU:-}"
    [[ -z "${g}" && -f "${OUTD}/gpu_mode.txt" ]] && g="$(cat "${OUTD}/gpu_mode.txt")"
    [[ -z "${g}" ]] && g=auto
    if [[ "${g}" == auto ]]; then
        if [[ "${SJ_ARCH}" == amd64 ]]; then g=gpus
        elif ls /etc/cdi/nvidia*.yaml /var/run/cdi/nvidia*.yaml >/dev/null 2>&1; then g=cdi
        else g=runtime; fi
    fi
    case "${g}" in
        gpus) echo "--gpus all" ;;
        cdi) echo "--device nvidia.com/gpu=all" ;;
        runtime) echo "--runtime nvidia -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=all" ;;
        none) echo "" ;;
        *) die "SJ_GPU must be auto|runtime|cdi|gpus|none (got ${g})" ;;
    esac
}

# sj_docker <name> <bash command string> [extra docker args...]
# One throw-away, isolated container (same isolation + thread caps as the desktop protocol: no network, private IPC,
# ROS_LOCALHOST_ONLY, 2-thread BLAS/OMP caps). Mounts only the package directory (same absolute path).
sj_docker() {
    local name="${SJ_PREFIX}_$1" cmd="$2"; shift 2
    local dom="${SJ_DOMAIN:-77}"
    # the main install is sourced explicitly (the image entrypoint also sources ws/install; this makes SJ_INSTALL_MAIN work)
    [[ "${SJ_NO_SOURCE:-0}" == 1 ]] || cmd="if [ -f ${INSTALL_MAIN}/setup.bash ]; then source ${INSTALL_MAIN}/setup.bash; fi; ${cmd}"
    local extra=()
    if [[ -n "${SJ_EXTRA_MOUNTS:-}" ]]; then
        local m; for m in ${SJ_EXTRA_MOUNTS}; do extra+=(-v "${m}"); done
    fi
    # shellcheck disable=SC2046
    local args=(run --rm --init -i --name "${name}" --network none --ipc private --shm-size "${SJ_SHM:-2g}"
        -v "${PKG_ROOT}:${PKG_ROOT}" "${extra[@]}"
        -e "SAVIOR_WS=${WS}" -e "SAVIOR_PLATFORM=${SJ_ARCH}" -e "ROS_DOMAIN_ID=${dom}" -e ROS_LOCALHOST_ONLY=1
        -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e MKL_NUM_THREADS=2 -e OPENCV_FOR_THREADS_NUM=4
        -e NUMEXPR_NUM_THREADS=2 -e SAVIOR_NUM_THREADS=2
        -e "HOME=${OUTD}/home" -e "YOLO_CONFIG_DIR=${OUTD}/home/ultralytics" -e "MPLCONFIGDIR=${OUTD}/home/mpl"
        -e "ROS_LOG_DIR=${OUTD}/roslog" -e "PKG_ROOT=${PKG_ROOT}" -e "SJ_ARCH=${SJ_ARCH}" -e YOLO_OFFLINE=1 -e "SJ_BACKEND=${SJ_BACKEND:-v1}"
        $(sj_gpu_args) "$@" -w "${WS}" "${SJ_IMAGE}" bash -c "${cmd}")
    mkdir -p "${OUTD}/home" "${OUTD}/roslog"
    if [[ "${SJ_DRYRUN:-0}" == 1 ]]; then
        printf 'DRYRUN docker'; printf ' %q' "${args[@]}"; echo
        return 0
    fi
    docker "${args[@]}"
}

# Refuse to start if one of OUR containers is still running (never touches anything else).
sj_require_idle_pkg() {
    local n
    n="$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c "^${SJ_PREFIX}_" || true)"
    [[ "${n}" -eq 0 ]] || die "${n} ${SJ_PREFIX}_* container(s) still running (docker ps); wait for them or remove ONLY those"
}

sj_require_image() {
    [[ "${SJ_DRYRUN:-0}" == 1 ]] && return 0
    docker image inspect "${SJ_IMAGE}" >/dev/null 2>&1 || die "image ${SJ_IMAGE} not found: run scripts/build_image.sh first"
}

sj_require_ws() {
    [[ "${SJ_DRYRUN:-0}" == 1 || "${SJ_FAKE_RUNS:-0}" == 1 ]] && return 0
    [[ -f "${INSTALL_MAIN}/setup.bash" ]] || die "missing ${INSTALL_MAIN}/setup.bash: run scripts/build_workspaces.sh first"
    [[ -f "${INSTALL_EDGE}/setup.bash" ]] || die "missing ${INSTALL_EDGE}/setup.bash: run scripts/build_workspaces.sh first"
}

# Python helpers always run INSIDE the image (numpy/yaml/matplotlib live there, nothing is installed on the host).
sj_py() {
    local name="$1"; shift
    local q; q="$(printf ' %q' "$@")"
    sj_docker "py_${name}" "python3 ${q}"
}
