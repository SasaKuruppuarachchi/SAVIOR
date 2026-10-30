#!/usr/bin/env python3
"""SAVIOR-Warehouse GT helpers for the P6 analysis: per-frame instance-id images (raw/<seq>/seg0|seg1), instance
classes, per-frame moving flags (moving.csv) and the carried-load relation (actor blocks of 16 ids).

Category of a GT instance in a frame (used everywhere in P6):
  moving_<cls>   the instance moves in this frame (true speed > 0.05 m/s, moving.csv)
  static_<cls>   a potentially-dynamic class (person / forklift / box / pallet / trolley) that does NOT move now
                 (parked forklifts, stacked pallets / boxes, rack boxes, standing people ...)
  struct         rack / guard_rail / window (static classes)
  bg             id 0 (walls, floor, ceiling, unlabelled props)
"""
import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

W = Path('/home/sasa/workspace/savior_ws/data/warehouse')
POT = ('person', 'forklift', 'box', 'pallet', 'trolley')
STRUCT = ('rack', 'guard_rail', 'window')


class SeqGT:
    def __init__(self, seq):
        self.seq = seq
        self.raw = W / 'raw' / seq
        inst = json.load(open(self.raw / 'instances.json'))['instances']
        self.max_id = max(i['id'] for i in inst)
        self.cls = {i['id']: i['cls'] for i in inst}
        self.info = {i['id']: i for i in inst}
        self.cls_lut = np.full(self.max_id + 1, '', object)
        for i in inst:
            self.cls_lut[i['id']] = i['cls']
        self.stamps = []
        self.moving = {}
        for ln in open(self.raw / 'moving.csv'):
            if ln.startswith('#'):
                continue
            k, s, ids = ln.rstrip('\n').split(',', 2)
            s = int(s)
            self.stamps.append(s)
            self.moving[s] = set(int(v) for v in ids.split()) if ids.strip() else set()
        self.stamps = np.array(self.stamps, np.int64)
        self.us_index = {int(round(s / 1000.0)): s for s in self.stamps}   # microsecond key -> ns stamp
        # class code LUT: 0 bg, 1..5 POT, 6 struct
        self.code = np.zeros(self.max_id + 1, np.uint8)
        for i, c in self.cls.items():
            self.code[i] = (POT.index(c) + 1) if c in POT else 6
        # actor blocks: forklift body id -> member ids (pallet / boxes / driver at +1..+15)
        self.block = {}
        for i, c in self.cls.items():
            if i >= 5000:
                self.block.setdefault((i - 5000) // 16, []).append(i)

    def stamp_from_sec(self, t):
        return self.us_index.get(int(round(t * 1e6)))

    @lru_cache(maxsize=64)
    def seg(self, cam, ns):
        a = cv2.imread(str(self.raw / f'seg{cam}' / f'{ns}.png'), cv2.IMREAD_UNCHANGED)
        return np.minimum(a, self.max_id)

    def category_image(self, cam, ns):
        """uint8 per pixel: 0 bg, 1..5 static POT class (person..trolley), 11..15 moving POT class, 6 struct, 16 moving struct."""
        ids = self.seg(cam, ns)
        code = self.code[ids].copy()
        mv = self.moving.get(ns, set())
        if mv:
            mm = np.isin(ids, np.fromiter(mv, np.int64))
            code[mm] += 10
        return code

    def carried_by(self, iid):
        """forklift body id of the actor block containing iid (iid itself not a forklift), else None."""
        if iid < 5000 or self.cls.get(iid) == 'forklift':
            return None
        blk = self.block.get((iid - 5000) // 16, [])
        f = [j for j in blk if self.cls.get(j) == 'forklift']
        return f[0] if f else None


CAT_NAMES = {0: 'bg', 6: 'struct', 16: 'moving_struct', **{k + 1: f'static_{c}' for k, c in enumerate(POT)},
             **{k + 11: f'moving_{c}' for k, c in enumerate(POT)}}
