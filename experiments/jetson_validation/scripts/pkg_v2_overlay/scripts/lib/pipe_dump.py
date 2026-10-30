#!/usr/bin/env python3
"""pipe_dump.py --seq SEQ --engine E --out OUT.npz [--edge] (v2, on-device validation)

Offline FULL SAVIOR perception pipeline (Python savior_perception SaviorPipeline, the reference implementation of the node)
on EVERY stereo frame of a t1 bag, with the live YOLO TensorRT segmenter built exactly as savior_node builds it
(make_segmenter with the node parameters, classes = roles relevant classes), the frozen sens_fix1 savior_node keys of
results/p7/final_config.yaml (+ segmenter.imgsz 672 for SAVIOR-edge, = the addendum pset) and the gyro rotation between
consecutive frames (GyroIntegrator, as results/cpp_port/.../equiv_offline.py). The pipeline does not depend on the
estimator, so its masks are a pure function of (bag, engine): the device-vs-desktop mask comparison isolates the
TensorRT engine / platform numerics.
Saved: stamps_ns[F], left_core / left_band / right_core [F, nbytes] (np.packbits of mask == 255 / == 192, H*W bits),
n_inst[F], n_roots[F], ms[F] (pipeline + predict wall ms), meta json. Run inside the image with the method's install sourced.
TUNING SET (t1) ONLY."""
import argparse, hashlib, json, os, time
from pathlib import Path
import numpy as np
import yaml


def flatten(d, prefix=''):
    out = {}
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            out.update(flatten(v, f'{prefix}{k}.'))
        else:
            out[f'{prefix}{k}'] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seq', required=True); ap.add_argument('--engine', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--edge', action='store_true'); ap.add_argument('--max-frames', type=int, default=0)
    a = ap.parse_args()
    assert '_t1_' in a.seq, 'tuning set (t1) only'
    WS = os.environ['SAVIOR_WS']
    B = f'{WS}/src/savior/savior_bringup/config'
    import cv2
    cv2.setNumThreads(int(os.environ.get('OPENCV_FOR_THREADS_NUM', '4')))
    from rosbags.highlevel import AnyReader
    from savior_perception.params import all_defaults
    from savior_perception.core.calibration import stereo_from_kalibr
    from savior_perception.core.config import PipelineConfig
    from savior_perception.core.pipeline import SaviorPipeline
    from savior_perception.core.roles import RoleTable
    from savior_perception.core.motion import GyroIntegrator
    from savior_perception.segmenters import make_segmenter
    import savior_perception
    P = all_defaults()
    P.update(flatten(yaml.safe_load(open(f'{B}/warehouse/savior_perception_yolo.yaml'))['savior_node']['ros__parameters']))
    F = yaml.safe_load(open(f'{WS}/results/p7/final_config.yaml'))
    P.update(F['methods']['sens_fix1']['savior_node'])
    if a.edge:
        P['segmenter.imgsz'] = 672
    roles = RoleTable.from_yaml(f'{B}/roles/warehouse.yaml')
    flat = {k: v for k, v in P.items() if k.split('.')[0] in PipelineConfig.SECTIONS}
    cfg = PipelineConfig.from_flat(flat)
    rect = stereo_from_kalibr(f'{B}/warehouse/kalibr_imucam_chain.yaml', 'cam0', 'cam1', focal_scale=cfg.depth.rect_focal_scale,
                              size_scale=cfg.depth.rect_size_scale, max_scale=cfg.depth.rect_max_scale)
    pipe = SaviorPipeline(cfg, roles, rect)
    seg = make_segmenter('yolo', model=a.engine, conf=P['segmenter.conf'], iou=P['segmenter.iou'], imgsz=P['segmenter.imgsz'],
                         device=P['segmenter.device'], half=P['segmenter.half'],
                         classes=roles.relevant_classes() if P['segmenter.filter_classes'] else None,
                         retina_masks=P['segmenter.retina_masks'], fast_masks=P['segmenter.fast_masks'])
    g = GyroIntegrator(max_age_s=1e9)
    frames = {}
    with AnyReader([Path(f'{WS}/data/warehouse/ros2_stereoseg/{a.seq}')]) as r:
        conns = [c for c in r.connections if c.topic in ('/imu0', '/cam0/image_raw', '/cam1/image_raw')]
        for c, _, raw in r.messages(connections=conns):
            m = r.deserialize(raw, c.msgtype)
            st = m.header.stamp.sec * 1_000_000_000 + m.header.stamp.nanosec
            if c.topic == '/imu0':
                w = m.angular_velocity
                g.add(st * 1e-9, (w.x, w.y, w.z))
            else:
                img = np.frombuffer(m.data, np.uint8).reshape(m.height, m.step)[:, :m.width].copy()
                frames.setdefault(st, [None, None])[0 if c.topic == '/cam0/image_raw' else 1] = img
    stamps = [s for s in sorted(frames) if frames[s][0] is not None and frames[s][1] is not None]
    if a.max_frames:
        stamps = stamps[:a.max_frames]
    seg.warmup(frames[stamps[0]][0].shape)
    LC, LB, RC, NI, NR, MS = [], [], [], [], [], []
    prev = None
    for st in stamps:
        left, right = frames[st]
        t = st * 1e-9
        R = g.rotation(prev, t) if prev is not None else None
        prev = t
        t0 = time.perf_counter()
        inst = seg.predict(left)
        ml, mr, stats = pipe.process(left, right, t, inst, R_imu=R)
        MS.append((time.perf_counter() - t0) * 1e3)
        LC.append(np.packbits((ml == 255).ravel())); LB.append(np.packbits((ml == 192).ravel()))
        RC.append(np.packbits((mr == 255).ravel()))
        NI.append(len(inst)); NR.append(int(stats.get('n_roots', -1)) if isinstance(stats, dict) else -1)
    import tensorrt, ultralytics
    try:
        import torch
        dev = torch.cuda.get_device_name(0)
    except Exception:  # noqa: BLE001
        dev = '?'
    meta = dict(seq=a.seq, engine=a.engine, engine_md5=hashlib.md5(open(a.engine, 'rb').read()).hexdigest(), edge=a.edge,
                tensorrt=tensorrt.__version__, ultralytics=ultralytics.__version__, device=dev, savior_perception=savior_perception.__file__,
                image_hw=list(frames[stamps[0]][0].shape[:2]), n_frames=len(stamps), cv2=cv2.__version__)
    np.savez_compressed(a.out, stamps_ns=np.array(stamps, np.int64), left_core=np.stack(LC), left_band=np.stack(LB), right_core=np.stack(RC),
                        n_inst=np.array(NI, np.int32), n_roots=np.array(NR, np.int32), ms=np.array(MS, np.float32), meta=json.dumps(meta))
    print(json.dumps(dict(meta, ms_median=float(np.median(MS)))), flush=True)


if __name__ == '__main__':
    main()
