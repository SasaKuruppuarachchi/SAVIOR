#!/usr/bin/env bash
# make_ros1_bag.sh <seq> <dst.bag> : ROS 2 mcap (DATASET=viode: data/viode/ros2/<seq>; DATASET=warehouse:
# data/warehouse/ros2_stereoseg/<seq>, images already mono8) -> ROS 1 bag with /cam0,/cam1 image_raw (rgb8,
# unchanged) + /imu0, using rosbags-convert in the savior image (no network), then verify counts/stamps.
set -euo pipefail
SEQ=$1; DST=$2
WS=${SAVIOR_WS:-/home/sasa/workspace/savior_ws}
D=$(cd "$(dirname "$0")" && pwd)
case ${DATASET:-viode} in viode) SRC=$WS/data/viode/ros2/$SEQ ;; warehouse) SRC=$WS/data/warehouse/ros2_stereoseg/$SEQ ;;
  *) echo "unknown DATASET $DATASET"; exit 2 ;; esac
mkdir -p "$(dirname "$DST")"; rm -f "$DST"
docker run --rm -i --name "sota_conv_${SEQ}_$$" --network none --ipc private -v $WS:$WS -v "$(dirname "$DST")":"$(dirname "$DST")" \
  -v "$D":"$D":ro -w /tmp savior:humble-cuda12.8 bash -c "set -e
  rosbags-convert --src $SRC --dst $DST --include-topic /cam0/image_raw /cam1/image_raw /imu0 \
     --src-typestore ros2_humble --dst-typestore ros1_noetic
  python3 -I $D/verify_ros1_bag.py $SRC $DST"
