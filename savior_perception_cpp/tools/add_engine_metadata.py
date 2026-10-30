#!/usr/bin/env python3
"""add_engine_metadata.py <reference.engine | metadata.json> <raw.engine> <out.engine>

Prepends the Ultralytics engine header (uint32 little-endian length + JSON metadata: class names, imgsz, stride, task) to a
raw TensorRT engine, e.g. one built on the Jetson with
    /usr/src/tensorrt/bin/trtexec --onnx=yolo26s-seg-warehouse.onnx --fp16 --saveEngine=raw.engine
so that savior_perception_cpp (and Ultralytics) read the class names / input size exactly as from an Ultralytics export.
The metadata is taken from a desktop Ultralytics .engine of the SAME model (or a JSON file). Only the plain Python standard
library is used (runs on the device without torch / ultralytics)."""
import json
import struct
import sys


def read_meta(path):
    with open(path, 'rb') as f:
        head = f.read(4)
        if path.endswith('.json'):
            return json.loads(head + f.read())
        (n,) = struct.unpack('<I', head)
        meta = f.read(n)
    if not meta.startswith(b'{'):
        raise SystemExit(f'{path}: no Ultralytics metadata header')
    return json.loads(meta.decode())


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    meta = read_meta(sys.argv[1])
    with open(sys.argv[2], 'rb') as f:
        raw = f.read()
    if len(raw) > 4 and raw[4:5] == b'{':
        raise SystemExit(f'{sys.argv[2]} already has a metadata header')
    blob = json.dumps(meta).encode()
    with open(sys.argv[3], 'wb') as f:
        f.write(struct.pack('<I', len(blob)))
        f.write(blob)
        f.write(raw)
    print(f'wrote {sys.argv[3]}: names={meta.get("names")} imgsz={meta.get("imgsz")}')


if __name__ == '__main__':
    main()
