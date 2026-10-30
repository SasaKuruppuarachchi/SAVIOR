#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fine-tune a COCO-pretrained YOLO26-seg on SAVIOR-Warehouse with the sim-to-real augmentation (simreal_aug.py).

  python3 train.py [--cfg train_cfg.yaml] [key=value ...]      e.g. model=.../yolo26n-seg.pt optimizer=auto name=n_auto
  python3 train.py --resume <run>/weights/last.pt [--epochs N]   resume (sim-to-real aug re-installed); --epochs
                                                                  shortens / extends the schedule of the checkpoint

key=value pairs override train_cfg.yaml (yaml-parsed values). The resolved config is written next to the run
(<project>/<name>/train_resolved.yaml) together with Ultralytics' own args.yaml.
"""
import argparse
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import simreal_aug  # noqa: E402

# train_cfg.yaml refers to $SAVIOR_WS (colcon workspace); default: <ws>/src/savior/savior_datasets/warehouse/train/../../../../..
os.environ.setdefault('SAVIOR_WS', os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cfg', default=os.path.join(HERE, 'train_cfg.yaml'))
    ap.add_argument('--resume', default='')
    ap.add_argument('--epochs', type=int, default=0)
    ap.add_argument('overrides', nargs='*')
    a = ap.parse_args()
    cfg = yaml.safe_load(open(a.cfg))
    for k in ('data', 'project', 'model'):
        if isinstance(cfg.get(k), str):
            cfg[k] = os.path.expandvars(cfg[k])
    if a.resume:
        return resume(a.resume, a.epochs, cfg.get('simreal_aug'))
    for kv in a.overrides:
        k, _, v = kv.partition('=')
        cfg[k] = yaml.safe_load(v)
        if isinstance(cfg[k], str):
            cfg[k] = os.path.expandvars(cfg[k])
    probs = cfg.pop('simreal_aug', None)
    if probs is not False:
        simreal_aug.install(probs or None)
    model = cfg.pop('model')
    out = os.path.join(cfg['project'], cfg['name'])
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'train_resolved.yaml'), 'w') as fh:
        yaml.safe_dump(dict(model=model, simreal_aug=probs, **cfg), fh, sort_keys=False)
    from ultralytics import YOLO
    YOLO(model).train(exist_ok=True, **cfg)


def resume(ckpt_path, epochs, probs):
    """Resume an interrupted run. With `epochs`, the checkpoint's train_args.epochs is rewritten first: the linear LR
    schedule (lambda over self.epochs) and close_mosaic (last 10 epochs) then follow the new length."""
    import torch
    if epochs:
        ck = torch.load(ckpt_path, map_location='cpu', weights_only=False)
        print(f"[train] {ckpt_path}: epoch {ck['epoch'] + 1} done, schedule {ck['train_args']['epochs']} -> {epochs} epochs")
        ck['train_args']['epochs'] = epochs
        torch.save(ck, ckpt_path)
    if probs is not False:
        simreal_aug.install(probs or None)
    from ultralytics import YOLO
    YOLO(ckpt_path).train(resume=True)


if __name__ == '__main__':
    main()
