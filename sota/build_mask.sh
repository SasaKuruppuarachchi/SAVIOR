#!/usr/bin/env bash
# build_mask.sh : savior-sota:noetic-mask = savior-sota:noetic + P9 (no network needed: sources are in the base image)
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
docker build --network none -t savior-sota:noetic-mask -f "$D/docker/Dockerfile.savior_mask" "$D" "$@"
docker run --rm --network none savior-sota:noetic-mask cat /opt/sota/COMMITS.txt
