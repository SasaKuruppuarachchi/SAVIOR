"""build_int8.py <s|n> : INT8 (+FP16 fallback) TensorRT engine of the warehouse YOLO26-seg at 384x672 from the workspace ONNX,
implicit entropy calibration (TensorRT IInt8EntropyCalibrator2) on 300 warehouse seg VAL images (gray x3, letterbox 114,
ultralytics preprocessing). The ultralytics metadata header is copied from the FP16 engine so YOLO() loads it.
-> engines/<m>672i8.engine (scratch only)."""
import glob, json, os, sys
import cv2
import numpy as np
import tensorrt as trt
import torch
m = sys.argv[1]
WS = '/home/sasa/workspace/savior_ws'
E = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge/engines'
onnx = f'{WS}/models/warehouse/yolo26{m}-seg-warehouse.onnx'
H, W = 384, 672
imgs = sorted(glob.glob(f'{WS}/data/warehouse/seg_train/yolo/images/val/*'))[:300]

def prep(p):
    im = cv2.imread(p)
    g = cv2.cvtColor(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    h, w = g.shape[:2]
    r = min(H / h, W / w)
    nh, nw = int(round(h * r)), int(round(w * r))
    g = cv2.resize(g, (nw, nh), interpolation=cv2.INTER_LINEAR)
    out = np.full((H, W, 3), 114, np.uint8)
    top, left = (H - nh) // 2, (W - nw) // 2
    out[top:top + nh, left:left + nw] = g
    return np.ascontiguousarray(out[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0)

class Calib(trt.IInt8EntropyCalibrator2):
    def __init__(self):
        super().__init__()
        self.i = 0
        self.buf = torch.zeros((1, 3, H, W), device='cuda')
        self.cache = f'{E}/calib_{m}672.cache'
    def get_batch_size(self):
        return 1
    def get_batch(self, names):
        if self.i >= len(imgs):
            return None
        self.buf.copy_(torch.from_numpy(prep(imgs[self.i])))
        self.i += 1
        return [int(self.buf.data_ptr())]
    def read_calibration_cache(self):
        return open(self.cache, 'rb').read() if os.path.isfile(self.cache) else None
    def write_calibration_cache(self, c):
        open(self.cache, 'wb').write(c)

logger = trt.Logger(trt.Logger.WARNING)
b = trt.Builder(logger)
net = b.create_network(0)
parser = trt.OnnxParser(net, logger)
assert parser.parse(open(onnx, 'rb').read()), [parser.get_error(i) for i in range(parser.num_errors)]
cfg = b.create_builder_config()
cfg.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 4 << 30)
cfg.set_flag(trt.BuilderFlag.INT8)
cfg.set_flag(trt.BuilderFlag.FP16)
cfg.int8_calibrator = Calib()
plan = b.build_serialized_network(net, cfg)
assert plan is not None, 'build failed'
src = f'{E}/{m}672.engine'
data = open(src, 'rb').read()
n = int.from_bytes(data[:4], 'little')
meta = json.loads(data[4:4 + n].decode())
hdr = json.dumps(meta).encode()
with open(f'{E}/{m}672i8.engine', 'wb') as f:
    f.write(len(hdr).to_bytes(4, 'little'))
    f.write(hdr)
    f.write(bytes(plan))
print('built', f'{E}/{m}672i8.engine', len(bytes(plan)) / 1e6, 'MB')
