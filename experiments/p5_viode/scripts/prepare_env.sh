#!/usr/bin/env bash
# prepare_env.sh <env>: unzip data/viode/raw/<env>.zip -> extracted/<env>/, inspect, convert each bag -> ros2/<env>_<level>/,
# GT (z-up, IMU frame) -> gt/<env>_<level>.txt, checks -> results/p5_viode/prep/. Runs the python tools inside the image.
set -euo pipefail
ENV=$1
WS=/home/sasa/workspace/savior_ws; V=$WS/data/viode; T=$WS/src/savior/savior_bringup/tools; P=$WS/results/p5_viode
SC=$P/scripts
mkdir -p $V/extracted/$ENV $V/ros2 $V/gt/masks $P/prep
cd $V/extracted/$ENV
if [[ ! -f .unzipped ]]; then unzip -o -q $V/raw/$ENV.zip -d $V/extracted/$ENV && touch .unzipped; fi
find $V/extracted/$ENV -name '*.bag' | sort
for BAG in $(find $V/extracted/$ENV -name '*.bag' | sort); do
  b=$(basename $BAG .bag); LEV=${b#*_}; SEQ=${ENV}_$LEV
  echo "== $BAG -> $SEQ"
  $SC/drun.sh 230 agentI_prep_${SEQ} bash -c "cd /tmp && \
    python3 -I $T/viode_prepare.py inspect --bag $BAG --out $P/prep/${SEQ}_inspect.yaml > /dev/null && \
    python3 -I $T/viode_prepare.py gt --bag $BAG --out $V/gt/$SEQ.txt --check-out $P/prep/${SEQ}_gtcheck.yaml > /dev/null && \
    python3 -I $T/viode_prepare.py imunoise --bag $BAG --out $P/prep/${SEQ}_imunoise.yaml > /dev/null && \
    python3 -I $T/viode_prepare.py segcolors --bag $BAG --rgb-ids $V/meta/segmentation/rgb_ids.txt --vehicle-ids $V/meta/segmentation/vehicle_ids_$ENV.txt --out $P/prep/${SEQ}_segcolors.yaml > /dev/null && \
    ( [[ -d $V/ros2/$SEQ ]] || python3 -I $T/bag1_to_ros2.py --src $BAG --dst $V/ros2/$SEQ --topics /cam0/image_raw /cam1/image_raw /cam0/segmentation /cam1/segmentation /imu0 /odometry ) && \
    python3 -I $SC/gt_masks.py $V/ros2/$SEQ $V/gt/masks/$SEQ.npz"
done
