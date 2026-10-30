#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""savior_bringup/tools/perception_offline.py for the SAVIOR-Warehouse bags (no ROS graph, deterministic).

perception_offline.py only knows the openloris_t265 / uhumans2 topic sets; this wrapper registers
`--dataset warehouse` (/cam0/image_raw, /cam1/image_raw, gyro /imu0) without touching the shared tool and then runs
its main() unchanged. Example (hall_t1_L2, warehouse role table, fine-tuned engine):

  python3 perception_offline_warehouse.py --dataset warehouse --bag data/warehouse/ros2/hall_t1_L2 \
      --params src/savior/savior_bringup/config/warehouse/savior_perception_yolo.yaml \
      --calib src/savior/savior_bringup/config/warehouse/kalibr_imucam_chain.yaml \
      --roles src/savior/savior_bringup/config/roles/warehouse.yaml \
      --set segmenter.model=models/warehouse/yolo26s-seg-warehouse.engine --stats /tmp/s.jsonl
"""
import os
import sys

WS = os.environ.get('SAVIOR_WS', os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..')))   # colcon workspace (<ws>/src/savior/...)
sys.path.insert(0, os.path.join(WS, 'src/savior/savior_bringup/tools'))
import perception_offline as po  # noqa: E402

po.TOPICS.setdefault('warehouse', ('/cam0/image_raw', '/cam1/image_raw'))
po.IMU_TOPICS.setdefault('warehouse', '/imu0')

if __name__ == '__main__':
    sys.exit(po.main())
