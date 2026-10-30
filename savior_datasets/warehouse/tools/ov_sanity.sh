#!/usr/bin/env bash
# Stock-OpenVINS sanity runs on converted SAVIOR-Warehouse bags, each trial in an isolated throw-away container
# (no network, own ROS domain -> no DDS cross-talk with other experiments that use the same topic names).
#   tools/ov_sanity.sh <seq> [offset ...]      (default offsets 0.0 0.3 0.6 s)
# Needs the workspace build (install/) + the savior_bringup overlay with config/warehouse (install_warehouse/):
#   colcon build --packages-select savior_bringup --build-base build_warehouse --install-base install_warehouse
set -euo pipefail
WS=${SAVIOR_WS:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)}
SEQ=$1; shift
OFFS=("$@"); [[ ${#OFFS[@]} -eq 0 ]] && OFFS=(0.0 0.3 0.6)
RES=${RES:-results/warehouse_sanity}
i=0
for off in "${OFFS[@]}"; do
  dom=$(( (RANDOM % 100) + 120 ))
  docker run --rm --init -i --network none --ipc private --shm-size 4g -v $WS:$WS -e SAVIOR_WS=$WS \
    -e ROS_DOMAIN_ID=$dom -e ROS_LOCALHOST_ONLY=1 -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 \
    -w $WS savior:humble-cuda12.8 bash -c "source install/setup.bash && source install_warehouse/setup.bash && \
    savior-run --bag data/warehouse/ros2/$SEQ --config \$(ros2 pkg prefix savior_bringup)/share/savior_bringup/config/warehouse/estimator_config.yaml \
      -n 1 --start-index $i --results-root $RES --dataset warehouse --seq $SEQ --method openvins \
      --launch-arg start_offset:=$off --gt data/warehouse/gt/$SEQ.txt" 2>&1 | grep -E "ATE|ok \(|FAIL|rror" || true
  i=$((i + 1))
done
