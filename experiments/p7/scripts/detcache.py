"""detcache.py <out_dir> <seq> [seq ...]: run the fine-tuned YOLO (deployed settings, fast_masks) on every left frame of
the t1 bags and cache the detections (class, score, bbox, packed crop mask) per frame -> <out_dir>/<seq>.npz.
The offline evaluator (p7eval.py) replays the SAVIOR pipeline variants on these cached detections (CPU only)."""
import sys, time
from pathlib import Path
import numpy as np
from rosbags.highlevel import AnyReader
from savior_perception.segmenters import make_segmenter
WS = '/home/sasa/workspace/savior_ws'
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
seg = make_segmenter('yolo', model=WS + '/models/warehouse/yolo26s-seg-warehouse.engine', conf=0.25, iou=0.7, imgsz=672,
                     classes=['person', 'forklift', 'box', 'pallet', 'trolley'], retina_masks=True, fast_masks=True)
for seq in sys.argv[2:]:
    assert '_t1_' in seq, 'tuning set only'
    t0 = time.time()
    stamps, nper, cls, score, bbox, bits = [], [], [], [], [], []
    with AnyReader([Path(f'{WS}/data/warehouse/ros2_stereoseg/{seq}')]) as r:
        conns = [c for c in r.connections if c.topic == '/cam0/image_raw']
        first = True
        for c, _, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()
            if first:
                seg.warmup(img.shape); first = False
            st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
            dets = seg.predict(img)
            stamps.append(st); nper.append(len(dets))
            for d in dets:
                x0, y0, x1, y1 = d.bbox
                cls.append(d.cls); score.append(d.score); bbox.append(d.bbox)
                bits.append(np.packbits(d.mask[y0:y1, x0:x1].ravel()))
    lens = np.array([len(b) for b in bits], np.int64)
    np.savez_compressed(out / f'{seq}.npz', stamps=np.array(stamps, np.int64), nper=np.array(nper, np.int64),
                        cls=np.array(cls), score=np.array(score, np.float32), bbox=np.array(bbox, np.int32).reshape(-1, 4),
                        bits=np.concatenate(bits) if bits else np.zeros(0, np.uint8), lens=lens, shape=np.array(img.shape[:2]))
    print(seq, len(stamps), 'frames', sum(nper), 'dets', round(time.time() - t0), 's', flush=True)
