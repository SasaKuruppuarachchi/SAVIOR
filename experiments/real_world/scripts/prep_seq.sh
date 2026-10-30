#!/usr/bin/env bash
# prep_seq.sh <SHORT> <zip basename>  e.g. prep_seq.sh MIO13 MIO13_moving_person
# Monado MSD Valve Index sequence -> data/monado/{prep,gt,ros2}: inspect, GT (gravity-up TUM, checks), zstd mcap bag with the
# stereo pairs OpenVINS tracks at track_frequency 28.35 (27 Hz of 54 Hz; IMU 1 kHz complete), count check.
set -euo pipefail
WS=/home/sasa/workspace/savior_ws; SH=$1; Z=$WS/data/monado/raw/$2.zip; T=$WS/src/savior/savior_bringup/tools/monado_prepare.py
D=$WS/data/monado; mkdir -p $D/prep $D/gt $D/ros2
docker run --rm --network none -u $(id -u):$(id -g) --name rw_prep_$SH -v $WS:$WS savior:humble-cuda12.8 bash -c "set -e
python3 -I $T inspect --zip $Z --out $D/prep/${SH}_inspect.yaml >/dev/null
python3 -I $T gt --zip $Z --out $D/gt/$SH.txt --check-out $D/prep/${SH}_gtcheck.yaml >/dev/null
python3 -I $T convert --zip $Z --dst $D/ros2/$SH --zstd --track-hz 28.35 > $D/prep/${SH}_convert.log
source /opt/ros/humble/setup.bash; ros2 bag info $D/ros2/$SH > $D/prep/${SH}_baginfo.txt"
python3 - "$D/prep/${SH}_inspect.yaml" "$D/prep/${SH}_convert.log" <<'PY'
import sys, yaml, re
I = yaml.safe_load(open(sys.argv[1])); L = open(sys.argv[2]).read()
c = {k: int(v) for k, v in re.findall(r'^(cam0|cam1|imu)\s+(\d+)$', L, re.M)}
assert c['cam0'] == c['cam1'] and c['imu'] == I['imu0']['n'] and abs(c['cam0'] - I['cam0']['n'] / 2) < 0.02 * I['cam0']['n'], (c, I)
print('counts OK', c)
PY
