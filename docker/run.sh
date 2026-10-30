#!/usr/bin/env bash
# Start (if needed) the long-running SAVIOR dev container and open an interactive shell in it.
#
# Usage: ./run.sh [--devices] [--recreate] [--stop] [-- <command> [args...]]
#   --devices   also pass host USB/video devices + udev (RealSense/ZED/serial sensors); privileged
#   --recreate  remove an existing container first (pick up new image / DISPLAY / options)
#   --stop      stop and remove the dev container, then exit
#   -- cmd      run cmd interactively instead of bash
#
# Subsequent ./run.sh calls attach new shells to the same container. Configuration via
# environment variables: see common.sh (SAVIOR_WS, SAVIOR_IMAGE, SAVIOR_CONTAINER, ...).
set -euo pipefail

usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

DEVICES=""
RECREATE=0
STOP=0
CMD=(bash)
while [[ $# -gt 0 ]]; do
    case "$1" in
        --devices) DEVICES=devices; shift ;;
        --recreate) RECREATE=1; shift ;;
        --stop) STOP=1; shift ;;
        -h | --help) usage ;;
        --) shift; [[ $# -gt 0 ]] && CMD=("$@"); break ;;
        *) echo "unknown option: $1" >&2; usage 1 ;;
    esac
done

# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

state="$(savior_container_state)"

if [[ "${STOP}" == 1 || ( "${RECREATE}" == 1 && -n "${state}" ) ]]; then
    if [[ -n "${state}" ]]; then
        savior_info "removing container ${SAVIOR_CONTAINER}"
        docker rm -f "${SAVIOR_CONTAINER}" >/dev/null
    fi
    state=""
    [[ "${STOP}" == 1 ]] && exit 0
fi

if [[ -z "${state}" ]]; then
    savior_check_image_user
    savior_run_args "${DEVICES}"
    savior_info "starting ${SAVIOR_CONTAINER} from ${SAVIOR_IMAGE} (workspace ${SAVIOR_WS})"
    docker run -d --init \
        --name "${SAVIOR_CONTAINER}" \
        --label "org.savior.devices=${DEVICES:-none}" \
        "${SAVIOR_RUN_ARGS[@]}" \
        -w "${SAVIOR_WS}" \
        "${SAVIOR_IMAGE}" sleep infinity >/dev/null
elif [[ "${state}" != "running" ]]; then
    savior_info "restarting existing container ${SAVIOR_CONTAINER} (use --recreate for a fresh one)"
    docker start "${SAVIOR_CONTAINER}" >/dev/null
fi

if [[ -n "${DEVICES}" && "$(docker container inspect -f '{{index .Config.Labels "org.savior.devices"}}' "${SAVIOR_CONTAINER}")" != "devices" ]]; then
    savior_info "warning: container was created without --devices; use ./run.sh --recreate --devices"
fi

TTY=(-i)
[[ -t 0 && -t 1 ]] && TTY=(-it)
exec docker exec "${TTY[@]}" -w "$(savior_workdir)" "${SAVIOR_CONTAINER}" savior-entrypoint "${CMD[@]}"
