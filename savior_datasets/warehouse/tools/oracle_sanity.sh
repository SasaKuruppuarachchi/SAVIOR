#!/usr/bin/env bash
# SAVIOR with PERFECT moving-object masks (dataset:=warehouse_moving, /cam0/segmentation_moving, all moving -> dynamic)
# on a SAVIOR-Warehouse bag, isolated containers as in ov_sanity.sh.   tools/oracle_sanity.sh <seq> [offset ...]
set -euo pipefail
WS=${SAVIOR_WS:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)}
SEQ=$1; shift
OFFS=("$@"); [[ ${#OFFS[@]} -eq 0 ]] && OFFS=(0.0 0.3 0.6)
RES=${RES:-results/warehouse_sanity}
START=${START:-0}
i=$START
for off in "${OFFS[@]}"; do
  dom=$(( (RANDOM % 100) + 120 ))
  docker run --rm --init -i --network none --ipc private --shm-size 4g -v $WS:$WS -e SAVIOR_WS=$WS \
    -e ROS_DOMAIN_ID=$dom -e ROS_LOCALHOST_ONLY=1 -e OMP_NUM_THREADS=2 -e OPENBLAS_NUM_THREADS=2 -e SAVIOR_NUM_THREADS=2 \
    -w $WS savior:humble-cuda12.8 bash -c "source install/setup.bash && source install_warehouse/setup.bash && \
    SHARE=\$(ros2 pkg prefix savior_bringup)/share/savior_bringup && \
    savior-run --launch-file savior.launch.py --bag data/warehouse/ros2/$SEQ --config \$SHARE/config/warehouse/estimator_config.yaml \
      -n 1 --start-index $i --results-root $RES --dataset warehouse --seq $SEQ --method oracle_moving \
      --launch-arg start_offset:=$off --launch-arg dataset:=warehouse_moving --launch-arg backend:=oracle_colormap \
      --launch-arg roles_file:=\$SHARE/config/roles/warehouse_oracle_moving.yaml --gt data/warehouse/gt/$SEQ.txt" 2>&1 \
      | grep -E "ATE|ok \(|FAIL|rror" || true
  i=$((i + 1))
done
