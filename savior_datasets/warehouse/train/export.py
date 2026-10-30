#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Export a fine-tuned warehouse YOLO26-seg to a TensorRT FP16 engine (desktop) and ONNX opset 17 (Jetson build).

Both use a static rectangular input of 384x672 (H x W): the 672x376 ZED 2i frames letterbox to 672x384 at scale 1.0
(8 px padding), 43 % fewer pixels than a 672x672 square. Static TensorRT engines carry their export shape in the
metadata and Ultralytics' predictor reuses it, so savior_node's `segmenter.imgsz` is ignored for them.

  python3 export.py --weights models/warehouse/yolo26s-seg-warehouse.pt [--formats engine,onnx]
-> <weights dir>/<stem>.engine (built for this GPU / TensorRT) and <stem>.onnx (opset 17, simplified)

Jetson Orin NX (JetPack 6.1, TensorRT 10.3): engines are not portable, build on the device. Preferred:
  yolo export model=yolo26s-seg-warehouse.pt format=engine imgsz=384,672 half=True workspace=2
(Ultralytics writes its metadata header - class names, imgsz, stride - in front of the plan; savior_node needs the
names for the role table). A bare plan from the ONNX file works with trtexec,
  /usr/src/tensorrt/bin/trtexec --onnx=yolo26s-seg-warehouse.onnx --fp16 --memPoolSize=workspace:2048 \
      --saveEngine=yolo26s-seg-warehouse.plan
but has no metadata: Ultralytics would name the classes class0..class7, so the warehouse role table would match
nothing. Use the ONNX/trtexec path only for profiling (trtexec --loadEngine) or prepend the metadata header.
"""
import argparse
import json
import os


def engine_info(path):
    import tensorrt as trt
    logger = trt.Logger(trt.Logger.WARNING)
    with open(path, 'rb') as fh:
        blob = fh.read()
    # Ultralytics prepends a 4-byte length + JSON metadata
    n = int.from_bytes(blob[:4], 'little')
    meta = json.loads(blob[4:4 + n].decode())
    eng = trt.Runtime(logger).deserialize_cuda_engine(blob[4 + n:])
    io = {eng.get_tensor_name(i): tuple(eng.get_tensor_shape(eng.get_tensor_name(i))) for i in range(eng.num_io_tensors)}
    dev_mem = getattr(eng, 'device_memory_size_v2', None) or eng.device_memory_size
    return dict(file_mb=os.path.getsize(path) / 2 ** 20, activation_mb=dev_mem / 2 ** 20, io=io,
                trt=trt.__version__, imgsz=meta.get('imgsz'), names=meta.get('names'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--weights', required=True)
    ap.add_argument('--imgsz', default='384,672')
    ap.add_argument('--formats', default='engine,onnx')
    ap.add_argument('--workspace', type=float, default=4.0)
    a = ap.parse_args()
    from ultralytics import YOLO
    imgsz = [int(v) for v in a.imgsz.split(',')]
    out = {}
    for fmt in a.formats.split(','):
        m = YOLO(a.weights)
        if fmt == 'engine':
            p = m.export(format='engine', imgsz=imgsz, half=True, device=0, simplify=True, workspace=a.workspace,
                         dynamic=False, batch=1)
            out['engine'] = dict(path=p, **engine_info(p))
        elif fmt == 'onnx':
            p = m.export(format='onnx', imgsz=imgsz, opset=17, simplify=True, dynamic=False, batch=1, device=0)
            import onnx
            mo = onnx.load(p)
            out['onnx'] = dict(path=p, file_mb=os.path.getsize(p) / 2 ** 20, opset=[o.version for o in mo.opset_import],
                               inputs=[(i.name, [d.dim_value for d in i.type.tensor_type.shape.dim]) for i in mo.graph.input],
                               outputs=[(o.name, [d.dim_value for d in o.type.tensor_type.shape.dim]) for o in mo.graph.output])
    print(json.dumps(out, indent=1, default=str))
    with open(os.path.splitext(a.weights)[0] + '_export.json', 'w') as fh:
        json.dump(out, fh, indent=1, default=str)


if __name__ == '__main__':
    main()
