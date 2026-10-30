# shellcheck shell=bash
# Shared settings for build.sh / run.sh / exec.sh. Not meant to be executed directly.
#
# Every value can be overridden through the environment:
#   SAVIOR_PLATFORM    amd64 | arm64            default: from `uname -m`
#   SAVIOR_IMAGE       image tag                default: savior:humble-cuda12.8 (amd64) / savior:humble-jp6 (arm64)
#   SAVIOR_WS          colcon workspace path    default: three levels above this directory (<ws>/src/savior/docker)
#   SAVIOR_CONTAINER   dev container name       default: savior-dev
#   SAVIOR_GPU         auto | gpus | cdi | runtime | none   how the GPU is passed in (default: auto)
#   SAVIOR_IPC         host | private           private => own /dev/shm of SAVIOR_SHM_SIZE (default: host)
#   SAVIOR_SHM_SIZE    /dev/shm size when SAVIOR_IPC=private (default: 8g)
#   SAVIOR_DOCKER_ARGS extra `docker run` arguments (word-split), e.g. "-v /mnt/data:/mnt/data"

SAVIOR_DOCKER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

savior_die() { echo "error: $*" >&2; exit 1; }
savior_info() { echo "[savior] $*" >&2; }

savior_host_platform() {
    case "$(uname -m)" in
        x86_64 | amd64) echo amd64 ;;
        aarch64 | arm64) echo arm64 ;;
        *) savior_die "unsupported architecture $(uname -m)" ;;
    esac
}

SAVIOR_PLATFORM="${SAVIOR_PLATFORM:-$(savior_host_platform)}"
case "${SAVIOR_PLATFORM}" in
    amd64) _savior_default_image="savior:humble-cuda12.8" ;;
    arm64) _savior_default_image="savior:humble-jp6" ;;
    *) savior_die "SAVIOR_PLATFORM must be amd64 or arm64 (got '${SAVIOR_PLATFORM}')" ;;
esac
SAVIOR_IMAGE="${SAVIOR_IMAGE:-${_savior_default_image}}"
SAVIOR_WS="${SAVIOR_WS:-$(cd "${SAVIOR_DOCKER_DIR}/../../.." && pwd)}"
SAVIOR_CONTAINER="${SAVIOR_CONTAINER:-savior-dev}"

[[ -d "${SAVIOR_WS}" ]] || savior_die "workspace '${SAVIOR_WS}' does not exist (set SAVIOR_WS)"
SAVIOR_WS="$(cd "${SAVIOR_WS}" && pwd -P)"

savior_container_state() {
    # Prints running | exited | created | ... or nothing if the container does not exist.
    docker container inspect -f '{{.State.Status}}' "${SAVIOR_CONTAINER}" 2>/dev/null || true
}

# Working directory inside the container: the caller's cwd if it is inside the workspace
# (same absolute path in the container), else the workspace root.
savior_workdir() {
    local cwd
    cwd="$(pwd -P)"
    if [[ "${cwd}" == "${SAVIOR_WS}" || "${cwd}" == "${SAVIOR_WS}/"* ]]; then
        echo "${cwd}"
    else
        echo "${SAVIOR_WS}"
    fi
}

# Fills the global array SAVIOR_RUN_ARGS with the `docker run` arguments.
# $1 = "devices" to also pass host USB/video devices (RealSense, ZED, ...).
savior_run_args() {
    local with_devices="${1:-}"
    SAVIOR_RUN_ARGS=(
        --network host # ROS 2 DDS discovery/transport with the host and other machines
        --ipc "${SAVIOR_IPC:-host}" # DDS shared-memory transport + large tensors in /dev/shm
        -v "${SAVIOR_WS}:${SAVIOR_WS}" # same absolute path as on the host
        -e "SAVIOR_WS=${SAVIOR_WS}"
        -e "SAVIOR_PLATFORM=${SAVIOR_PLATFORM}"
        -e "TERM=${TERM:-xterm-256color}"
    )
    if [[ "${SAVIOR_IPC:-host}" != "host" ]]; then
        SAVIOR_RUN_ARGS+=(--shm-size "${SAVIOR_SHM_SIZE:-8g}")
    fi

    # Pass through ROS networking settings if set on the host.
    local var
    for var in ROS_DOMAIN_ID ROS_LOCALHOST_ONLY RMW_IMPLEMENTATION CYCLONEDDS_URI FASTRTPS_DEFAULT_PROFILES_FILE \
               SAVIOR_MODELS_DIR SAVIOR_CACHE_DIR; do
        if [[ -n "${!var:-}" ]]; then SAVIOR_RUN_ARGS+=(-e "${var}=${!var}"); fi
    done

    # GPU access.
    local gpu="${SAVIOR_GPU:-auto}"
    if [[ "${gpu}" == "auto" ]]; then
        if [[ "${SAVIOR_PLATFORM}" == "amd64" ]]; then
            gpu=gpus
        elif grep -qsE '"?kind"?: *"?nvidia\.com/gpu' /etc/cdi/*.yaml /etc/cdi/*.json /var/run/cdi/*.yaml /var/run/cdi/*.json 2>/dev/null; then
            gpu=cdi # JetPack 6 + NVIDIA Container Toolkit >= 1.16 can generate a GPU CDI spec (a PVA-only spec,
                    # /etc/cdi/nvidia-pva.yaml on stock JetPack 6.2, does not count: then --runtime nvidia)
        else
            gpu=runtime # legacy nvidia runtime (CSV mounts of the L4T libraries)
        fi
    fi
    case "${gpu}" in
        gpus) SAVIOR_RUN_ARGS+=(--gpus all) ;;
        cdi) SAVIOR_RUN_ARGS+=(--device nvidia.com/gpu=all) ;;
        runtime) SAVIOR_RUN_ARGS+=(--runtime nvidia -e NVIDIA_VISIBLE_DEVICES=all) ;;
        none) ;;
        *) savior_die "SAVIOR_GPU must be auto|gpus|cdi|runtime|none (got '${gpu}')" ;;
    esac

    # Jetson extras: tegrastats / jtop for power+timing measurements.
    if [[ "${SAVIOR_PLATFORM}" == "arm64" ]]; then
        [[ -x /usr/bin/tegrastats ]] && SAVIOR_RUN_ARGS+=(-v /usr/bin/tegrastats:/usr/bin/tegrastats:ro)
        [[ -S /run/jtop.sock ]] && SAVIOR_RUN_ARGS+=(-v /run/jtop.sock:/run/jtop.sock:ro)
    fi

    # X11 (rviz2): only if the host has a display. Harmless otherwise.
    if [[ -n "${DISPLAY:-}" ]]; then
        SAVIOR_RUN_ARGS+=(-e "DISPLAY=${DISPLAY}")
        [[ -d /tmp/.X11-unix ]] && SAVIOR_RUN_ARGS+=(-v /tmp/.X11-unix:/tmp/.X11-unix:rw)
        local xauth="${XAUTHORITY:-${HOME}/.Xauthority}"
        if [[ -f "${xauth}" ]]; then
            SAVIOR_RUN_ARGS+=(-v "${xauth}:/tmp/.savior.xauth:ro" -e XAUTHORITY=/tmp/.savior.xauth)
        fi
        [[ -e /dev/dri ]] && SAVIOR_RUN_ARGS+=(--device /dev/dri)
    fi

    # Sensors (RealSense / ZED / serial IMUs): whole /dev + udev, needs privileged for hot-plug.
    if [[ "${with_devices}" == "devices" ]]; then
        SAVIOR_RUN_ARGS+=(--privileged -v /dev:/dev -v /run/udev:/run/udev:ro)
    fi

    if [[ -n "${SAVIOR_DOCKER_ARGS:-}" ]]; then
        # shellcheck disable=SC2206
        SAVIOR_RUN_ARGS+=(${SAVIOR_DOCKER_ARGS})
    fi
}

# Warn if the image was built for a different uid/gid than the calling user (files in the
# workspace would get the wrong owner).
savior_check_image_user() {
    local img_ids
    img_ids="$(docker image inspect -f '{{index .Config.Labels "org.savior.uid"}}:{{index .Config.Labels "org.savior.gid"}}' "${SAVIOR_IMAGE}" 2>/dev/null)" \
        || savior_die "image ${SAVIOR_IMAGE} not found; run ${SAVIOR_DOCKER_DIR}/build.sh first"
    if [[ "${img_ids}" != "$(id -u):$(id -g)" ]]; then
        savior_info "warning: ${SAVIOR_IMAGE} was built for uid:gid ${img_ids}, you are $(id -u):$(id -g)." \
            "Files written to the workspace will be owned by ${img_ids}. Rebuild with ./build.sh."
    fi
}
