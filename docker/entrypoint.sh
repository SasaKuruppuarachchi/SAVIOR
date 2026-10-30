#!/usr/bin/env bash
# SAVIOR container entrypoint.
#
# - Sources ROS 2 Humble and, if it has been built, the mounted colcon workspace overlay.
# - Points model/cache directories into the mounted workspace (nothing is stored in the image).
# - Executed: sets up the environment, then runs the given command (default: bash).
#   Sourced (from /etc/bash.bashrc): only sets up the environment.
#
# Environment (normally passed by run.sh / exec.sh):
#   SAVIOR_WS          absolute path of the colcon workspace (mounted at the same path as on the host)
#   SAVIOR_MODELS_DIR  model weights / TensorRT engines      default: $SAVIOR_WS/models
#   SAVIOR_CACHE_DIR   caches (ultralytics, torch, ...)      default: $SAVIOR_WS/.cache

# Guard against double sourcing (bash.bashrc + entrypoint in the same shell).
if [[ -z "${_SAVIOR_ENV_DONE:-}" ]]; then
    export _SAVIOR_ENV_DONE=1

    # shellcheck disable=SC1090,SC1091
    source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"

    if [[ -n "${SAVIOR_WS:-}" ]]; then
        export SAVIOR_MODELS_DIR="${SAVIOR_MODELS_DIR:-${SAVIOR_WS}/models}"
        export SAVIOR_CACHE_DIR="${SAVIOR_CACHE_DIR:-${SAVIOR_WS}/.cache}"
        export YOLO_CONFIG_DIR="${YOLO_CONFIG_DIR:-${SAVIOR_CACHE_DIR}/ultralytics}"
        export TORCH_HOME="${TORCH_HOME:-${SAVIOR_CACHE_DIR}/torch}"
        export MPLCONFIGDIR="${MPLCONFIGDIR:-${SAVIOR_CACHE_DIR}/matplotlib}"

        if [[ -f "${SAVIOR_WS}/install/setup.bash" ]]; then
            # shellcheck disable=SC1091
            source "${SAVIOR_WS}/install/setup.bash" \
                || echo "[savior-entrypoint] warning: failed to source ${SAVIOR_WS}/install/setup.bash" >&2
        fi
    fi
fi

# Interactive shells: tab completion for ros2 / colcon (functions are not inherited, so this is
# outside the guard).
if [[ $- == *i* ]]; then
    for _f in "/opt/ros/${ROS_DISTRO:-humble}/share/ros2cli/environment/ros2-argcomplete.bash" \
              /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash; do
        # shellcheck disable=SC1090
        [[ -f "${_f}" ]] && source "${_f}"
    done
    unset _f
fi

# Stop here when sourced.
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    return 0
fi

if [[ -n "${SAVIOR_WS:-}" && -w "${SAVIOR_WS}" ]]; then
    mkdir -p "${SAVIOR_MODELS_DIR}" "${YOLO_CONFIG_DIR}" "${TORCH_HOME}" "${MPLCONFIGDIR}" 2>/dev/null || true
    # One-time ultralytics settings: keep weights/runs/datasets inside the workspace instead of the
    # (ephemeral) container home or the current directory.
    # (ultralytics stores it as $YOLO_CONFIG_DIR/Ultralytics/settings.json)
    if [[ ! -f "${YOLO_CONFIG_DIR}/Ultralytics/settings.json" ]]; then
        python3 - <<'EOF' >/dev/null 2>&1 || echo "[savior-entrypoint] warning: could not initialise ultralytics settings" >&2
import os
from ultralytics.utils import SETTINGS
ws = os.environ["SAVIOR_WS"]
SETTINGS.update(weights_dir=os.environ["SAVIOR_MODELS_DIR"],
                runs_dir=os.path.join(ws, "results", "ultralytics"),
                datasets_dir=os.path.join(ws, "data", "ultralytics"),
                sync=False)
EOF
    fi
fi

if [[ $# -eq 0 ]]; then
    set -- bash
fi
exec "$@"
