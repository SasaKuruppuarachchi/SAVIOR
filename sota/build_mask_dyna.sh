#!/usr/bin/env bash
# build_mask_dyna.sh : savior-sota:noetic-mask-dyna = savior-sota:noetic + P10 (DynaVINS + SAVIOR masks; no network)
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
docker build --network none -t savior-sota:noetic-mask-dyna -f "$D/docker/Dockerfile.savior_mask_dyna" "$D" "$@"
docker run --rm --network none savior-sota:noetic-mask-dyna cat /opt/sota/COMMITS.txt
