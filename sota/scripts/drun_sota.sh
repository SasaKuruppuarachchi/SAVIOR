#!/usr/bin/env bash
# drun_sota.sh <name> <bag_dir> cmd... : isolated throw-away savior-sota container (no network, own ipc, CPU cap)
set -euo pipefail
NAME=$1; BAGDIR=$2; shift 2
WS=${SAVIOR_WS:-/home/sasa/workspace/savior_ws}
exec docker run --rm --init -i --name "$NAME" --user "$(id -u):$(id -g)" --network none --ipc private --cpus "${SOTA_CPUS:-4}" \
  -v $WS:$WS -v "$BAGDIR":"$BAGDIR":ro ${SOTA_ROOT:+-v $SOTA_ROOT:$SOTA_ROOT} -e OMP_NUM_THREADS=2 -e SOTA_SEQ -e SOTA_DATASET -e SOTA_IMAGE=${SOTA_IMAGE:-savior-sota:noetic} \
  -e SOTA_MASK_DIR -e SOTA_MASK_MODE -e SOTA_MASK_THRESHOLD -e SOTA_MASK_RELAXED -e SOTA_MASK_MIN_FEATURES -e SOTA_MASK_LATENCY_MS \
  -e SOTA_MASK_WAIT_MS -e SOTA_DETERMINISTIC -e SOTA_IGNORE_SOLVER_TIME \
  -w /tmp ${SOTA_IMAGE:-savior-sota:noetic} "$@"
