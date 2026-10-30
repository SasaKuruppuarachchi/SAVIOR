#!/usr/bin/env bash
# build_workspaces.sh - colcon-build the two FROZEN source trees inside the image (nothing is edited):
#   main  ws/src/savior              -> ws/build, ws/install                          (OpenVINS, Y-Cls, SAVIOR = sens_fix1)
#   edge  ws/frozen_edge/src/savior  -> ws/frozen_edge/build, ws/frozen_edge/install  (SAVIOR-edge)
# Same command as the desktop builds (colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release, the 8 packages of the desktop
# install), but serial packages + SJ_JOBS make jobs to fit 8 GB RAM. Verifies the tree hashes before and after.
# Time: ~40-90 min for both on an Orin NX (OpenVINS C++ dominates). Disk: ~4 GB. Log: out/logs/build_ws_{main,edge}.log
# Usage: scripts/build_workspaces.sh [main|edge|both]      Env: SJ_JOBS (default 2; 3 if MemAvailable > 6 GB)
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
WHICH="${1:-both}"
sj_require_image; sj_require_idle_pkg
python3 "${LIB}/verify_trees.py" --quiet || die "package integrity check failed before the build"
mema=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
JOBS="${SJ_JOBS:-$( (( mema > 6000 )) && echo 3 || echo 2)}"
PKGS="ov_core ov_data ov_eval ov_init ov_msckf savior_bringup savior_eval savior_perception"
build_one() {  # build_one <tag> <base dir containing src/>
    local tag="$1" base="$2" t0; t0=$(date +%s)
    log "build_ws: ${tag} (${base}/src) with MAKEFLAGS=-j${JOBS}, packages: ${PKGS}"
    local cmd="export MAKEFLAGS=-j${JOBS}; cd ${base} && colcon --log-base ${base}/log build --base-paths ${base}/src \
--build-base ${base}/build --install-base ${base}/install --packages-select ${PKGS} --executor sequential \
--event-handlers console_cohesion+ --cmake-args -DCMAKE_BUILD_TYPE=Release"
    if ! SJ_NO_SOURCE=1 sj_docker "build_${tag}" "${cmd}" > "${OUTD}/logs/build_ws_${tag}.log" 2>&1; then
        tail -40 "${OUTD}/logs/build_ws_${tag}.log"
        echo "HINTS (not applied): 'c++: fatal error: Killed signal' = out of memory -> rerun with SJ_JOBS=1;" \
             "missing dependency -> the image is incomplete (report to the user; do not apt-get install on the host)." >&2
        die "colcon build ${tag} failed (log out/logs/build_ws_${tag}.log)"
    fi
    log "build_ws: ${tag} done in $(( ($(date +%s) - t0) / 60 )) min"
}
# v2: 'cpp' = the C++ savior_node overlay (results/cpp_port/source_git 237640ee: savior_perception_cpp, savior_ov_component,
# perception_impl savior_bringup) in ws/cpp_port -> ws/cpp_port/install, on top of ws/install (sm_87, JetPack TensorRT in /usr,
# system OpenCV 4.5.4 = the desktop 'final' variant)
build_cpp() {
    local base="${WS}/cpp_port" t0; t0=$(date +%s)
    log "build_ws: cpp (${base}/src) with MAKEFLAGS=-j${JOBS}"
    local cmd="export MAKEFLAGS=-j${JOBS}; source ${INSTALL_MAIN}/setup.bash; cd ${base} && colcon --log-base ${base}/log build --base-paths ${base}/src \
--build-base ${base}/build --install-base ${base}/install --packages-select savior_perception_cpp savior_ov_component savior_bringup --executor sequential \
--event-handlers console_cohesion+ --cmake-args -DCMAKE_BUILD_TYPE=Release -DSAVIOR_BUILD_PYTHON=OFF \
$( [[ "${SJ_ARCH}" == arm64 ]] && echo '-DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc -DCMAKE_CUDA_ARCHITECTURES=87 -DTENSORRT_ROOT=/usr' )"
    if ! SJ_NO_SOURCE=1 sj_docker "build_cpp" "${cmd}" > "${OUTD}/logs/build_ws_cpp.log" 2>&1; then
        tail -40 "${OUTD}/logs/build_ws_cpp.log"; die "colcon build cpp failed (log out/logs/build_ws_cpp.log)"
    fi
    log "build_ws: cpp done in $(( ($(date +%s) - t0) / 60 )) min"
    sj_docker build_check_cpp "source ${base}/install/local_setup.bash; ros2 pkg executables savior_perception_cpp; \
ldd ${base}/install/savior_perception_cpp/lib/savior_perception_cpp/savior_node_cpp | grep -E 'nvinfer|opencv_core|cudart|yaml|not found' || true" | tee "${OUTD}/logs/build_ws_cpp_check.log"
}
if [[ "${WHICH}" == cpp ]]; then build_cpp; exit 0; fi
[[ "${WHICH}" == main || "${WHICH}" == both ]] && build_one main "${WS}"
[[ "${WHICH}" == edge || "${WHICH}" == both ]] && build_one edge "${WS}/frozen_edge"
python3 "${LIB}/verify_trees.py" --quiet --no-manifest || die "frozen tree hashes changed during the build (should be impossible)"
# smoke: both installs resolve the packages + executables
CHK="set -e; for I in ${INSTALL_MAIN} ${INSTALL_EDGE}; do (source \$I/setup.bash; \
echo \$I; ros2 pkg prefix ov_msckf; ros2 pkg prefix savior_perception; ros2 pkg executables ov_msckf | tr '\n' ' '; echo; \
python3 -c 'import savior_perception, savior_eval; print(savior_perception.__file__)'; \
ldd \$(ros2 pkg prefix ov_msckf)/lib/ov_msckf/run_subscribe_msckf | grep 'not found' && exit 3 || true); done; which savior-run savior-eval"
sj_docker build_check "${CHK}" | tee "${OUTD}/logs/build_ws_check.log"
log "build_ws: OK (main + edge installs usable)"
