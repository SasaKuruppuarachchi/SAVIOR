#!/usr/bin/env bash
# prep_bag.sh <env> <n_level> (e.g. parking_lot 0_none): extract ONE bag from the zip, inspect / GT / IMU noise / seg
# colours, convert to ROS 2 (seg -> mono8 ids), GT masks, verify message counts, delete the extracted ROS 1 bag.
set -euo pipefail
ENV=$1; NL=$2; LEV=${NL#*_}; SEQ=${ENV}_$LEV
WS=/home/sasa/workspace/savior_ws; V=$WS/data/viode; T=$WS/src/savior/savior_bringup/tools; P=$WS/results/p5_viode
BAG=$V/extracted/$ENV/$NL.bag
mkdir -p $V/extracted $V/ros2 $V/gt/masks $P/prep
[[ -f $BAG ]] || unzip -o -q $V/raw/$ENV.zip $ENV/$NL.bag -d $V/extracted/
M=$V/meta/segmentation
$P/scripts/drun.sh 229 agentI_prep_$SEQ bash -c "cd /tmp && set -e && \
  python3 -I $T/viode_prepare.py inspect --bag $BAG --out $P/prep/${SEQ}_inspect.yaml > /dev/null && \
  python3 -I $T/viode_prepare.py gt --bag $BAG --out $V/gt/$SEQ.txt --check-out $P/prep/${SEQ}_gtcheck.yaml > /dev/null && \
  python3 -I $T/viode_prepare.py imunoise --bag $BAG --out $P/prep/${SEQ}_imunoise.yaml > /dev/null && \
  python3 -I $T/viode_prepare.py segcolors --every 10 --bag $BAG --rgb-ids $M/rgb_ids.txt --vehicle-ids $M/vehicle_ids_$ENV.txt --out $P/prep/${SEQ}_segcolors.yaml > /dev/null && \
  ( [[ -d $V/ros2/$SEQ ]] || python3 -I $T/viode_prepare.py convert --bag $BAG --dst $V/ros2/$SEQ --rgb-ids $M/rgb_ids.txt > $P/prep/${SEQ}_convert.log ) && \
  python3 -I $P/scripts/gt_masks.py $V/ros2/$SEQ $V/gt/masks/$SEQ.npz > $P/prep/${SEQ}_gtmasks.log && \
  python3 -I -c \"
import yaml, sys
a = yaml.safe_load(open('$P/prep/${SEQ}_inspect.yaml'))['topics']
b = {t['name']: t['message_count'] for t in yaml.safe_load(open('$V/ros2/$SEQ/metadata.yaml'))['rosbag2_bagfile_information']['topics_with_message_count'] for t in [t['topic_metadata'] | {'message_count': t['message_count']}]}
bad = [k for k in ('/cam0/image_raw', '/cam1/image_raw', '/cam0/segmentation', '/cam1/segmentation', '/imu0', '/odometry') if a[k]['count'] != b.get(k)]
print('verify', '$SEQ', 'OK' if not bad else 'MISMATCH %s' % bad)
sys.exit(1 if bad else 0)
\" > $P/prep/${SEQ}_verify.log"
cat $P/prep/${SEQ}_verify.log
grep -q OK $P/prep/${SEQ}_verify.log && rm -f $BAG && echo "deleted $BAG"
