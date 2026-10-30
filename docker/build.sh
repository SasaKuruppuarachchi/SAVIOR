#!/usr/bin/env bash
# Build the SAVIOR dev image for this machine's architecture (x86_64 desktop or Jetson aarch64).
#
# Usage: ./build.sh [--platform amd64|arm64] [--tag IMAGE] [--no-cache] [-- <extra docker build args>]
#
# The image is built for the calling user's uid/gid so files written to the mounted workspace
# keep the right owner. Building for a foreign architecture (e.g. --platform arm64 on a desktop)
# requires QEMU binfmt emulation and is very slow; build on the target instead.
#
# Env SAVIOR_BUILD_NETWORK: network mode of the RUN steps. Default: "host" for a native build on an
# aarch64 host (Jetson: the L4T kernel lacks the netfilter/bridge features BuildKit's per-step network
# sandbox needs -> "Perhaps iptables or your kernel needs to be upgraded"), BuildKit's default elsewhere.
# Set SAVIOR_BUILD_NETWORK=default to force BuildKit's default.
set -euo pipefail

usage() { sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

EXTRA=()
NO_CACHE=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --platform) SAVIOR_PLATFORM="$2"; shift 2 ;;
        --tag) SAVIOR_IMAGE="$2"; shift 2 ;;
        --no-cache) NO_CACHE=(--no-cache); shift ;;
        -h | --help) usage ;;
        --) shift; EXTRA=("$@"); break ;;
        *) echo "unknown option: $1" >&2; usage 1 ;;
    esac
done

# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

PLATFORM_ARGS=()
if [[ "${SAVIOR_PLATFORM}" != "$(savior_host_platform)" ]]; then
    savior_info "cross-building ${SAVIOR_PLATFORM} on a $(savior_host_platform) host (needs QEMU, slow)"
    PLATFORM_ARGS=(--platform "linux/${SAVIOR_PLATFORM}")
fi

NETWORK_ARGS=()
_net="${SAVIOR_BUILD_NETWORK:-}"
if [[ -z "${_net}" && "${SAVIOR_PLATFORM}" == arm64 && "$(savior_host_platform)" == arm64 ]]; then _net=host; fi
if [[ -n "${_net}" && "${_net}" != default ]]; then NETWORK_ARGS=(--network "${_net}"); savior_info "RUN steps use --network ${_net}"; fi

savior_info "building ${SAVIOR_IMAGE} (PLATFORM=${SAVIOR_PLATFORM}, uid:gid $(id -u):$(id -g))"
DOCKER_BUILDKIT=1 docker build \
    "${PLATFORM_ARGS[@]}" "${NO_CACHE[@]}" "${NETWORK_ARGS[@]}" \
    --build-arg "PLATFORM=${SAVIOR_PLATFORM}" \
    --build-arg "USER_UID=$(id -u)" \
    --build-arg "USER_GID=$(id -g)" \
    --target dev \
    -t "${SAVIOR_IMAGE}" \
    "${EXTRA[@]}" \
    "${SAVIOR_DOCKER_DIR}"

savior_info "done: $(docker image inspect -f '{{.Id}}' "${SAVIOR_IMAGE}") ${SAVIOR_IMAGE}"
