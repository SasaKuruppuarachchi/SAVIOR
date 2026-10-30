#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Reproduce the SAVIOR dataset preparation (run INSIDE the ROS 2 Humble container, workspace mounted at
# the same absolute path). Never executes anything shipped with the datasets.
#
#   bash prepare_datasets.sh uhumans2  <ws>      # uHumans2 office_s1_00h (add more bags in the loop below)
#   bash prepare_datasets.sh openloris <ws>      # OpenLORIS-Scene T265 sequences (cafe1-*, office1-*, market1-1)
#
# Outputs (never committed; OpenLORIS is CC BY-ND 4.0 -> keep local):
#   <ws>/data/uhumans2/ros2/<seq>/   <ws>/data/uhumans2/gt/<seq>.txt   (TUM, IMU = base_link_gt frame)
#   <ws>/data/openloris/extracted/   <ws>/data/openloris/ros2/<seq>/   <ws>/data/openloris/gt/<seq>.txt (TUM, T265 IMU frame)
set -euo pipefail
WHAT=${1:?uhumans2|openloris}
WS=${2:-${SAVIOR_WS:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}}
T=$(cd "$(dirname "$0")" && pwd)
PY="python3 -I"

case "$WHAT" in
uhumans2)
  for seq in ${UH_SEQS:-office_s1_00h office_s1_06h office_s1_12h}; do
    BAG=$WS/data/uhumans2/uHumans2_${seq}.bag
    $PY "$T/uhumans2_prepare.py" inspect --fast --bag "$BAG" --out "$WS/data/uhumans2/inspect_${seq}.yaml"
    $PY "$T/uhumans2_prepare.py" gt --bag "$BAG" --out "$WS/data/uhumans2/gt/${seq}.txt"
    $PY "$T/uhumans2_prepare.py" imunoise --bag "$BAG" --out "$WS/data/uhumans2/imu_noise_${seq}.yaml"
    $PY "$T/bag1_to_ros2.py" --src "$BAG" --dst "$WS/data/uhumans2/ros2/${seq}" --topics \
      /tesse/left_cam/mono/image_raw /tesse/right_cam/mono/image_raw \
      /tesse/left_cam/camera_info /tesse/right_cam/camera_info /tesse/left_cam/rgb/image_raw \
      /tesse/seg_cam/rgb/image_raw /tesse/seg_cam/camera_info \
      /tesse/imu/clean/imu /tesse/imu/noisy/imu /tesse/imu/noisy/biases/accel /tesse/imu/noisy/biases/gyro \
      /tesse/odom /tf /tf_static /clock
    ros2 bag info "$WS/data/uhumans2/ros2/${seq}"
  done
  ;;
openloris)
  D=$WS/data/openloris
  # 1) extract archives into their own new directories (the bundled decompress.sh is NOT run;
  #    rosbags reads the bz2/lz4-compressed bags directly)
  for a in cafe1-1_2-rosbag office1-1_7-rosbag; do
    [ -d "$D/extracted/$a" ] || { mkdir -p "$D/extracted/$a"; tar xf "$D/raw/$a.tar" -C "$D/extracted/$a" --no-same-owner --no-same-permissions; }
  done
  [ -d "$D/extracted/groundtruth" ] || { mkdir -p "$D/extracted/groundtruth"; (cd "$D/extracted/groundtruth" && unzip -q "$D/raw/groundtruth.zip"); }
  # 2) per sequence: ROS 2 conversion (+ gyro/accel merge, 8UC1 -> mono8), GT in the T265 IMU frame
  for BAG in "$D"/extracted/cafe1-1_2-rosbag/*.bag "$D"/extracted/office1-1_7-rosbag/*.bag "$D"/raw/market1-1.bag; do
    seq=$(basename "$BAG" .bag)
    [ -d "$D/ros2/$seq" ] || $PY "$T/openloris_prepare.py" convert --bag "$BAG" --dst "$D/ros2/$seq"
    $PY "$T/openloris_prepare.py" gt --bag "$BAG" --gt "$D/extracted/groundtruth/per-sequence/$seq/groundtruth.txt" --out "$D/gt/$seq.txt"
    $PY "$T/openloris_prepare.py" gt --frame base_link --bag "$BAG" --gt "$D/extracted/groundtruth/per-sequence/$seq/groundtruth.txt" --out "$D/gt/base_link/$seq.txt"
  done
  # 3) calibration -> savior_bringup/config/openloris_t265/kalibr_imucam_chain{,_market}.yaml
  $PY "$T/openloris_prepare.py" calib --bag "$D/extracted/cafe1-1_2-rosbag/cafe1-1.bag"
  $PY "$T/openloris_prepare.py" calib --bag "$D/raw/market1-1.bag"
  ;;
*) echo "unknown dataset $WHAT"; exit 1 ;;
esac
