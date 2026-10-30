#!/usr/bin/env bash
# Run one command inside the SAVIOR environment, non-interactively, and return its exit code.
#
# Usage: ./exec.sh [--devices] <command> [args...]
#   e.g. ./exec.sh colcon build --symlink-install
#        ./exec.sh bash -c 'source install/setup.bash && ros2 launch ...'
#        ./exec.sh savior-check-env
#
# Uses the running dev container (./run.sh) if there is one, otherwise a throw-away container
# (docker run --rm). The working directory is the caller's cwd when it lies inside the workspace,
# else the workspace root. ROS 2 and the workspace overlay (install/setup.bash) are sourced.
set -euo pipefail

usage() { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

DEVICES=""
case "${1:-}" in
    --devices) DEVICES=devices; shift ;;
    -h | --help) usage ;;
    "") usage 1 ;;
esac
[[ $# -gt 0 ]] || usage 1

# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

TTY=(-i)
[[ -t 0 && -t 1 ]] && TTY=(-it)
WORKDIR="$(savior_workdir)"

if [[ "$(savior_container_state)" == "running" ]]; then
    exec docker exec "${TTY[@]}" -w "${WORKDIR}" "${SAVIOR_CONTAINER}" savior-entrypoint "$@"
fi

savior_check_image_user
savior_run_args "${DEVICES}"
exec docker run --rm --init "${TTY[@]}" "${SAVIOR_RUN_ARGS[@]}" -w "${WORKDIR}" "${SAVIOR_IMAGE}" "$@"
