"""prof_seg.py <seq> [n_frames] : profile the YOLO segmenter stages on frames of a t1 bag (idle GPU)."""
import sys, time
from pathlib import Path
import numpy as np
from rosbags.highlevel import AnyReader
from savior_perception.segmenters import make_segmenter
WS = '/home/sasa/workspace/savior_ws'
seq = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 300
imgs = []
with AnyReader([Path(f'{WS}/data/warehouse/ros2_stereoseg/{seq}')]) as r:
    conns = [c for c in r.connections if c.topic == '/cam0/image_raw']
    for k, (c, _, raw) in enumerate(r.messages(connections=conns)):
        if k % 5: continue
        m = r.deserialize(raw, c.msgtype)
        imgs.append(np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy())
        if len(imgs) >= N: break
seg = make_segmenter('yolo', model=WS + '/models/warehouse/yolo26s-seg-warehouse.engine', conf=0.25, iou=0.7, imgsz=672,
                     classes=['person', 'forklift', 'box', 'pallet', 'trolley'], retina_masks=True)
seg.warmup(imgs[0].shape)
T, S, n = [], [], []
for im in imgs:
    t0 = time.perf_counter(); out = seg.predict(im); T.append((time.perf_counter() - t0) * 1e3); n.append(len(out))
    S.append(seg.model.predictor.results[0].speed if hasattr(seg.model.predictor, 'results') else {})
T = np.array(T)
print(seq, 'frames', len(T), 'inst/frame median', np.median(n), 'max', max(n))
print('predict() ms median %.1f p90 %.1f p99 %.1f' % tuple(np.percentile(T, [50, 90, 99])))
