#!/usr/bin/env python3
"""mkbackend_v2.py : write the OpenVINS back-end v2 config directories under results/backend_v2/config/ (host python).

Back-end v2 = the frozen estimator_config.yaml with ONLY two keys changed (results/ov_diag variant trk10_clones15):
    track_frequency: 21.0 -> 10.5   (clone / track every 2nd 20 Hz frame)
    max_clones:      11   -> 15     (window 11 x 50 ms = 0.55 s -> 15 x 100 ms = 1.5 s)
Every other file of the dataset config directory is copied VERBATIM (md5 asserted), because savior.launch.py takes
kalibr_imucam_chain.yaml (calib) and savior_perception.yaml (perception defaults of the oracle methods) from the
directory of the estimator yaml, and the dataset name (topics, colormap) from the directory NAME. So:
    config/warehouse/              <- src/savior/savior_bringup/config/warehouse   (used by all t1 / t2 runs)
    config/frozen_edge/warehouse/  <- frozen_edge/src/savior/savior_bringup/config/warehouse (byte-identical inputs)
    config/viode/                  <- src/savior/savior_bringup/config/viode        (prepared for the held-out run only)
The sources are only read (src/, frozen_edge/, the frozen yamls are never modified).
"""
import hashlib
import re
import shutil
import sys
from pathlib import Path

WS = Path('/home/sasa/workspace/savior_ws')
OUT = WS / 'results/backend_v2/config'
CHANGE = {'track_frequency': '10.5', 'max_clones': '15'}
TAG = 'BACKEND-V2 2026-10-24, results/ov_diag trk10_clones15'
SRC = {
    'warehouse': (WS / 'src/savior/savior_bringup/config/warehouse', 'b18ac56386df56a1c33898550127c670'),
    'frozen_edge/warehouse': (WS / 'frozen_edge/src/savior/savior_bringup/config/warehouse', 'b18ac56386df56a1c33898550127c670'),
    'viode': (WS / 'src/savior/savior_bringup/config/viode', '54b296c2fef63c46b3e072683074227f'),
}


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def sub(text, key, val):
    pat = re.compile(r'^(' + re.escape(key) + r':\s*)([^#\n]*?)(\s*(#.*)?)$', re.M)
    n = len(pat.findall(text))
    if n != 1:
        sys.exit(f'key {key} found {n}x')
    return pat.sub(lambda m: m.group(1) + val + f'  # {TAG} (was {m.group(2).strip()})' + (' ' + m.group(4) if m.group(4) else ''), text)


for name, (src, want) in SRC.items():
    est = src / 'estimator_config.yaml'
    assert md5(est) == want, f'{est} changed ({md5(est)})'
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    t = est.read_text()
    for k, v in CHANGE.items():
        t = sub(t, k, v)
    (d / 'estimator_config.yaml').write_text(t)
    for f in sorted(src.iterdir()):
        if f.name != 'estimator_config.yaml' and f.is_file():
            shutil.copyfile(f, d / f.name)
            assert md5(f) == md5(d / f.name)
    print(name, 'estimator v2', md5(d / 'estimator_config.yaml'), '| copies:',
          ', '.join(f'{f.name} {md5(f)[:8]}' for f in sorted(d.iterdir()) if f.name != 'estimator_config.yaml'))
