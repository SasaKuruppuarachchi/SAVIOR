"""Shared helpers for the P5 VIODE scripts (run inside the savior image, python3 -I with PYTHONPATH set by the caller)."""
import numpy as np

META = '/home/sasa/workspace/savior_ws/data/viode/meta'
ENVS = ['parking_lot', 'city_day', 'city_night']
LEVELS = ['none', 'low', 'mid', 'high']
SEQS = [f'{e}_{l}' for e in ENVS for l in LEVELS]


def rgb_ids():
    ids = {}
    for line in open(f'{META}/segmentation/rgb_ids.txt'):
        p = [x.strip() for x in line.split(',')]
        if len(p) == 4 and p[0].isdigit():
            ids[int(p[0])] = tuple(int(v) for v in p[1:])
    return ids


def vehicle_ids(env):
    veh = {}
    for line in open(f'{META}/segmentation/vehicle_ids_{env}.txt'):
        p = [x.strip() for x in line.split(',')]
        if len(p) == 2 and p[0].isdigit():
            veh[int(p[0])] = p[1]
    return veh


class IdDecoder:
    """RGB segmentation image -> object id image (uint8; colours not in rgb_ids.txt -> 0)."""
    def __init__(self):
        ids = rgb_ids()
        keys = np.array([(r << 16) | (g << 8) | b for (r, g, b) in ids.values()], np.int64)
        vals = np.array(list(ids.keys()), np.int64)
        o = np.argsort(keys)
        self.keys, self.vals = keys[o], vals[o]

    def __call__(self, rgb):
        k = (rgb[..., 0].astype(np.int64) << 16) | (rgb[..., 1].astype(np.int64) << 8) | rgb[..., 2]
        i = np.clip(np.searchsorted(self.keys, k), 0, len(self.keys) - 1)
        out = np.where(self.keys[i] == k, self.vals[i], 0)
        return out.astype(np.uint8)


def decode_image(msg):
    """sensor_msgs/Image (rosbags) -> uint8 array; colour images returned as RGB, plus encoding."""
    enc = msg.encoding.lower()
    ch = 1 if enc in ('mono8', '8uc1') else (4 if enc in ('bgra8', 'rgba8') else 3)
    a = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)[:, :msg.width * ch]
    a = a.reshape(msg.height, msg.width, ch) if ch > 1 else a.reshape(msg.height, msg.width)
    if ch >= 3:
        a = a[:, :, :3]
        if enc.startswith('bgr'):
            a = a[:, :, ::-1]
    return np.ascontiguousarray(a)
