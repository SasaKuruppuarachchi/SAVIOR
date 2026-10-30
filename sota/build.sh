#!/usr/bin/env bash
# build.sh : build savior-sota:noetic (host network for fetching the pinned sources; nothing else uses the network)
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
docker build --network host -t savior-sota:noetic -f "$D/docker/Dockerfile" --build-arg JOBS=${JOBS:-8} "$D" "$@"
docker run --rm --network none savior-sota:noetic cat /opt/sota/COMMITS.txt
docker images savior-sota:noetic
