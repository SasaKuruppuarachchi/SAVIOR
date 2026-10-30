"""stage breakdown of YoloSegmenter.predict (ultralytics pre/infer/post + SAVIOR conversion)."""
import sys, time
from pathlib import Path
import numpy as np, cv2
from rosbags.highlevel import AnyReader
from savior_perception.segmenters import make_segmenter
from savior_perception.core.types import Instance, mask_bbox
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
rows = []
for im in imgs:
    img = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    t0 = time.perf_counter()
    res = seg.model.predict(img, conf=0.25, iou=0.7, imgsz=672, retina_masks=True, verbose=False, classes=seg.class_ids)[0]
    t1 = time.perf_counter()
    masks = (res.masks.data > 0.5).cpu().numpy() if res.masks is not None else np.zeros((0,)+im.shape, bool)
    t2 = time.perf_counter()
    boxes = res.boxes.xyxy.cpu().numpy(); out = []
    for i in range(masks.shape[0]):
        m = np.ascontiguousarray(masks[i]); tb = mask_bbox(m)
        if tb is None: continue
        out.append(Instance(mask=m, cls='x', score=1.0, bbox=tuple(boxes[i])))
    t3 = time.perf_counter()
    sp = res.speed
    rows.append([sp['preprocess'], sp['inference'], sp['postprocess'], (t1 - t0) * 1e3, (t2 - t1) * 1e3, (t3 - t2) * 1e3, len(out)])
A = np.array(rows)
for j, nm in enumerate(['ul_pre', 'ul_infer', 'ul_post', 'ul_total', 'to_cpu', 'instances', 'n']):
    print('%-10s median %.2f p90 %.2f p99 %.2f' % (nm, *np.percentile(A[:, j], [50, 90, 99])))
