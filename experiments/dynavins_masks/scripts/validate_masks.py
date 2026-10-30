#!/usr/bin/env python3
"""validate_masks.py <mask root> <split t1|t2|viode> <out.json> : checks that the exported SAVIOR masks are the right ones
for DynaVINS (runs in the savior image: numpy, cv2, yaml).
Per <seq>/<method>/off_<o>: export_info seq/method/offset == path; n_fail = n_unsynced = imu_timeouts = 0; index.csv rows
= n_frames and recomputed masks_md5 == export_info; left/ and right/ file sets == index stamps; every file is a hard
link of pool/<md5 in index>.png; every pool file decodes to mono8 of the image size with md5(pixels) == its name;
first stamp >= bag start + offset; export_info param overrides == frozen_params.method_params() today (frozen p7
yamls); band (192) pixels present only for the *_ext (band) methods. zero/off_all: all pixels 0."""
import csv, glob, hashlib, json, os, sys
import cv2, numpy as np, yaml
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/sota/mask_export')
import frozen_params  # noqa: E402

ROOT, SPLIT, OUT = sys.argv[1:4]
METHODS = ['sens_fix1', 'savior_edge', 'yolo_naive', 'oracle_moving_ext', 'oracle_class_ext']
if SPLIT == 't1':
    SEQS = [f'{e}_t1_L{l}' for e in ('aisles', 'hall') for l in range(4)]
elif SPLIT == 't2':
    SEQS = [f'{e}_t2_L{l}' for e in ('aisles', 'hall', 'dock') for l in range(4)]
else:
    SEQS = [f'{e}_{l}' for e in ('parking_lot', 'city_day', 'city_night') for l in ('none', 'low', 'mid', 'high')]
pool_ok = {}


def check_pool(pool, h, shape):
    k = (pool, h)
    if k not in pool_ok:
        m = cv2.imread(os.path.join(pool, h + '.png'), cv2.IMREAD_UNCHANGED)
        pool_ok[k] = (m is not None and m.dtype == np.uint8 and m.ndim == 2 and (shape is None or m.shape == shape)
                      and hashlib.md5(m.tobytes()).hexdigest() == h, None if m is None else m.shape,
                      None if m is None else sorted(np.unique(m).tolist()))
    return pool_ok[k]


res, errors = [], []
Z = {}  # all left stamps of the bag (zero/off_all/index.csv is written from every left image message)
for s_ in SEQS:
    f = f'{ROOT}/{s_}/zero/off_all/index.csv'
    if os.path.isfile(f):
        Z[s_] = sorted(int(r['stamp_ns']) for r in csv.DictReader(open(f)))
for s in SEQS:
    for m in METHODS + ['zero']:
        mdir = f'{ROOT}/{s}/{m}'
        pool = mdir + '/pool'
        offs = sorted(glob.glob(mdir + '/off_*'))
        if not offs:
            errors.append(f'{s}/{m}: no export'); continue
        P = None
        if m != 'zero':
            try:
                P = frozen_params.method_params(s, m)
            except Exception as e:  # noqa: BLE001
                errors.append(f'{s}/{m}: frozen_params failed {e}')
        for od in offs:
            e = []
            rows = list(csv.DictReader(open(od + '/index.csv')))
            st = [int(r['stamp_ns']) for r in rows]
            info = yaml.safe_load(open(od + '/export_info.yaml')) if m != 'zero' else None
            if info is not None:
                o = float(od.rsplit('off_', 1)[1])
                if info['seq'] != s or info['method'] != m or abs(info['start_offset'] - o) > 1e-9:
                    e.append('export_info identity mismatch')
                for k in ('n_fail', 'n_unsynced', 'imu_timeouts'):
                    if info.get(k, 0):
                        e.append(f'{k}={info[k]}')
                if info['n_frames'] != len(rows):
                    e.append('n_frames != index rows')
                h = hashlib.md5()
                for r in rows:
                    h.update(f"{r['stamp_ns']}{r['md5_left']}{r['md5_right']}".encode())
                if h.hexdigest() != info['masks_md5']:
                    e.append('masks_md5 mismatch')
                if P is not None and (info['overrides'] != P['overrides'] or info['param_files'] != P['param_files']):
                    e.append('parameters differ from frozen_params today')
                if Z.get(s) and st:
                    z = Z[s]
                    tail = [x for x in z if x >= st[0]]
                    if st != tail:
                        e.append(f'stamps != bag left stamps from the first exported frame ({len(st)} vs {len(tail)})')
                    lag = (st[0] - z[0]) * 1e-9 - o
                    if not (-1e-6 <= lag < 0.051):
                        e.append(f'first stamp {lag:+.3f} s from bag start + offset')
            for side, col in (('left', 'md5_left'), ('right', 'md5_right')):
                files = {int(f[:-4]) for f in os.listdir(f'{od}/{side}') if f.endswith('.png')}
                if files != set(st):
                    e.append(f'{side} file set != index ({len(files)} vs {len(st)})')
                for r in rows:
                    fp = f"{od}/{side}/{r['stamp_ns']}.png"
                    pp = f"{pool}/{r[col]}.png"
                    if not os.path.exists(fp) or not os.path.exists(pp) or os.stat(fp).st_ino != os.stat(pp).st_ino:
                        e.append(f'{side} {r["stamp_ns"]} not a link of its pool file'); break
                for h in {r[col] for r in rows}:
                    ok, shape, vals = check_pool(pool, h, None)
                    if not ok:
                        e.append(f'pool {h} bad'); break
                    if m == 'zero' and vals != [0]:
                        e.append('zero mask not all-zero'); break
            band = sum(int(r['band_left']) + int(r['band_right']) for r in rows)
            core = sum(int(r['core_left']) + int(r['core_right']) for r in rows)
            if m.endswith('_ext') and band == 0 and core > 0:   # (no movers at L0: empty oracle-moving masks)
                e.append('band method without band pixels')
            if not m.endswith('_ext') and band > 0:
                e.append('band pixels in a no-band method')
            res.append(dict(seq=s, method=m, off=od.rsplit('/', 1)[1], frames=len(rows), first=st[0] if st else None,
                            core_px=core, band_px=band, masks_md5=None if info is None else info['masks_md5'], errors=e))
            errors += [f'{s}/{m}/{od.rsplit("/", 1)[1]}: {x}' for x in e]
summ = dict(split=SPLIT, root=ROOT, n_dirs=len(res), n_pool_files_checked=len(pool_ok),
            n_errors=len(errors), errors=errors[:200])
json.dump(dict(summary=summ, dirs=res), open(OUT, 'w'), indent=1)
print(json.dumps(summ, indent=1))
