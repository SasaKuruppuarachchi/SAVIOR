"""detcache_edge.py <engine key> [seq ...]: like results/p7/scripts/detcache.py (deployed settings, fast_masks) for an EDGE
engine (engines/<key>.engine) -> detcache/<key>/<seq>.npz, plus the per-frame segment wall time [ms] (predict incl. mask
transfer; GPU shared with other users: use for RELATIVE comparisons only, interleaved runs)."""
import sys, time
from pathlib import Path
import numpy as np
from rosbags.highlevel import AnyReader
from savior_perception.segmenters import make_segmenter
WS = '/home/sasa/workspace/savior_ws'
E = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge'
key = sys.argv[1]
eng = WS + '/models/warehouse/yolo26s-seg-warehouse.engine' if key == 'ws' else f'{E}/engines/{key}.engine'
imgsz = {'672': 672, '512': 512, '416': 416}[key[1:4]] if key != 'ws' else 672
out = Path(f'{E}/detcache/{key}'); out.mkdir(parents=True, exist_ok=True)
seg = make_segmenter('yolo', model=eng, conf=0.25, iou=0.7, imgsz=imgsz,
                     classes=['person', 'forklift', 'box', 'pallet', 'trolley'], retina_masks=True, fast_masks=True)
for seq in sys.argv[2:]:
    assert '_t1_' in seq, 'tuning set only'
    if (out / f'{seq}.npz').exists():
        continue
    t0 = time.time()
    stamps, nper, cls, score, bbox, bits, ms = [], [], [], [], [], [], []
    with AnyReader([Path(f'{WS}/data/warehouse/ros2_stereoseg/{seq}')]) as r:
        conns = [c for c in r.connections if c.topic == '/cam0/image_raw']
        first = True
        for c, _, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()
            if first:
                for _ in range(20):
                    seg.warmup(img.shape)
                first = False
            st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
            c0 = time.perf_counter()
            dets = seg.predict(img)
            ms.append((time.perf_counter() - c0) * 1e3)
            stamps.append(st); nper.append(len(dets))
            for d in dets:
                x0, y0, x1, y1 = d.bbox
                cls.append(d.cls); score.append(d.score); bbox.append(d.bbox)
                bits.append(np.packbits(d.mask[y0:y1, x0:x1].ravel()))
    lens = np.array([len(b) for b in bits], np.int64)
    np.savez_compressed(out / f'{seq}.npz', stamps=np.array(stamps, np.int64), nper=np.array(nper, np.int64),
                        cls=np.array(cls), score=np.array(score, np.float32), bbox=np.array(bbox, np.int32).reshape(-1, 4),
                        bits=np.concatenate(bits) if bits else np.zeros(0, np.uint8), lens=lens, shape=np.array(img.shape[:2]),
                        seg_ms=np.array(ms, np.float32))
    print(key, seq, len(stamps), 'frames', sum(nper), 'dets', round(time.time() - t0), 's', 'seg ms med', round(float(np.median(ms)), 2), flush=True)
