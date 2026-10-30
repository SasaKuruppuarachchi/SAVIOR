"""export_engines.py: TensorRT engines of the fine-tuned warehouse YOLO26 (n / s) at several input sizes, FP16 and INT8
(calibration: the warehouse segmentation VAL split, fraction 0.25). Written into the EDGE scratch only."""
import os, shutil, sys, time
from ultralytics import YOLO
E = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge/engines'
DATA = '/home/sasa/workspace/savior_ws/data/warehouse/seg_train/yolo/data.yaml'
SIZES = {'672': (384, 672), '512': (288, 512), '416': (224, 416)}
todo = sys.argv[1:] or ['s672', 'n672', 's512', 'n512', 's416', 'n416', 's672i8', 'n672i8', 's512i8', 'n512i8']
for name in todo:
    out = f'{E}/{name}.engine'
    if os.path.isfile(out):
        continue
    m, sz, i8 = name[0], name[1:4], name.endswith('i8')
    src = f'{E}/{m}.pt'
    work = f'{E}/work_{name}'
    os.makedirs(work, exist_ok=True)
    shutil.copy(src, f'{work}/{name}.pt')
    t0 = time.time()
    kw = dict(format='engine', imgsz=SIZES[sz], device=0, batch=1, simplify=True, workspace=4)
    if i8:
        kw.update(int8=True, data=DATA, fraction=0.25)
    else:
        kw.update(half=True)
    p = YOLO(f'{work}/{name}.pt', task='segment').export(**kw)
    shutil.move(p, out)
    print(name, 'exported', round(time.time() - t0), 's', out, flush=True)
