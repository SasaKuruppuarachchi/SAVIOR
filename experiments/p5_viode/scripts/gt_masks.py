#!/usr/bin/env python3
"""gt_masks.py <ros2 bag dir> <out npz>: vehicle-id images of /cam0/segmentation and /cam1/segmentation
(uint8: 0 = no vehicle, else the AirSim object id of a vehicle listed in vehicle_ids_<env>.txt), keyed by stamp_ns.
Also writes per-frame dynamic / static vehicle pixel shares."""
import sys
from pathlib import Path

import numpy as np
from rosbags.highlevel import AnyReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from viode_common import IdDecoder, decode_image, vehicle_ids  # noqa: E402

bag, out = sys.argv[1], sys.argv[2]
env = Path(bag).name.rsplit('_', 1)[0]
veh = vehicle_ids(env)
lut = np.zeros(256, np.uint8)
for i in veh:
    lut[i] = i
dec = IdDecoder()
data = {'/cam0/segmentation': {}, '/cam1/segmentation': {}}
with AnyReader([Path(bag)]) as r:
    conns = [c for c in r.connections if c.topic in data]
    for c, _, raw in r.messages(connections=conns):
        m = r.deserialize(raw, c.msgtype)
        st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
        img = decode_image(m)
        data[c.topic][st] = lut[img if img.ndim == 2 else dec(img)]   # mono8 = id image (viode_prepare.py convert)
st = sorted(set(data['/cam0/segmentation']) & set(data['/cam1/segmentation']))
L = np.stack([data['/cam0/segmentation'][s] for s in st])
R = np.stack([data['/cam1/segmentation'][s] for s in st])
dyn_ids = np.array(sorted(i for i, n in veh.items() if 'dynamic' in n))
sta_ids = np.array(sorted(i for i, n in veh.items() if 'static' in n))
dyn_share = np.isin(L, dyn_ids).mean(axis=(1, 2))
sta_share = np.isin(L, sta_ids).mean(axis=(1, 2))
np.savez_compressed(out, stamp_ns=np.array(st, np.int64), left=L, right=R, dyn_ids=dyn_ids, static_ids=sta_ids,
                    dyn_share=dyn_share, static_share=sta_share)
print(f'{bag}: {len(st)} frames, dyn share mean {dyn_share.mean():.4f} max {dyn_share.max():.4f}, '
      f'static share mean {sta_share.mean():.4f}, frames dyn>5% {(dyn_share > 0.05).mean():.3f}')
