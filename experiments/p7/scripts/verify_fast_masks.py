"""verify_fast_masks.py <seq> [n]: segmenter fast_masks=True vs the P2-P6 path on the same frames: masks / bboxes / classes /
scores must be identical; timing of predict() per path (idle GPU)."""
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
        if k % 4: continue
        m = r.deserialize(raw, c.msgtype)
        imgs.append(np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy())
        if len(imgs) >= N: break
kw = dict(model=WS + '/models/warehouse/yolo26s-seg-warehouse.engine', conf=0.25, iou=0.7, imgsz=672,
          classes=['person', 'forklift', 'box', 'pallet', 'trolley'], retina_masks=True)
seg = make_segmenter('yolo', **kw)
seg.warmup(imgs[0].shape)
bad = 0; ninst = 0; T = {False: [], True: []}
for im in imgs:
    outs = {}
    for fast in (False, True):
        seg.fast_masks = fast
        t0 = time.perf_counter(); outs[fast] = seg.predict(im); T[fast].append((time.perf_counter() - t0) * 1e3)
    a, b = outs[False], outs[True]
    ninst += len(a)
    if len(a) != len(b) or any(x.cls != y.cls or x.score != y.score or x.bbox != y.bbox or not np.array_equal(x.mask, y.mask)
                               for x, y in zip(a, b)):
        bad += 1
print(f'{seq}: frames {len(imgs)} instances {ninst} frames_with_differences {bad}')
for f in (False, True):
    print('fast_masks=%s predict ms median %.2f p90 %.2f p99 %.2f' % (f, *np.percentile(T[f], [50, 90, 99])))
