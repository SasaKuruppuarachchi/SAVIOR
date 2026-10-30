#!/usr/bin/env python3
"""nv_audit.py : validity audit (PROTOCOL.yaml validity section) of every NIS-validation run AND of every paired baseline run, plus the
learned NIS lambda of every NIS run ([SAVIOR-GATE] lines) and the md5-identity controls.
  warehouse t2 / VIODE / task E : results/review_runs/scripts/rr_audit.py rules (end tolerance 0.101 s, reference = same-offset
                                  openvins(-v2) / e_openvins run of the frozen baseline set)
  Monado                        : results/real_world/scripts/rw_analyze.py rules incl. the Amendment-2 frame rule
-> tables/audit.csv, tables/audit.md, tables/invalid.txt (own runs: '<set> <seq> <variant> run_XX'), tables/invalid_baselines.txt,
   tables/lambda_runs.csv. Run inside the image (scripts/nvpy.sh python3 scripts/nv_audit.py)."""
import csv, glob, gzip, hashlib, os, re, sys
import yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nv_plan import DATASETS, NV, R, VARIANTS, baseline_dir, run_dir  # noqa: E402
T = NV + '/tables'
FIN = re.compile(r'FINAL: .*?(\d+) measurements .*?exact=(\d+) fallback_latest=(\d+) fallback_empty=(\d+) late_masks=(\d+)')
GATE = re.compile(r'\[SAVIOR-GATE\]: (\w+) updates=(\d+) tested bg/static/band=(\d+)/(\d+)/(\d+) rejected=(\d+)/(\d+)/(\d+) nis_lambda=([\d.]+)')
EXP = yaml.safe_load(open(R + '/real_world/prep/expected_frames.yaml'))
LO, HI = 0.05, 20.0


def stamps(f):
    return [float(l.split()[0]) for l in open(f) if l.strip() and not l.startswith('#')] if os.path.isfile(f) else []


def md5(f):
    return hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else ''


def opn(f):
    return gzip.open(f, 'rt', errors='replace') if f.endswith('.gz') else open(f, errors='replace')


def scan(rd):
    r = dict(status='?', final='-', fb=0, late=0, in_core=0, frames=0, savior=False, gate=[])
    try:
        ri = yaml.safe_load(open(f'{rd}/run_info.yaml')) or {}
        r['status'] = f"{ri.get('status')}/{ri.get('returncode', 0)}"
        r['savior'] = 'savior.launch.py' in str(ri.get('cmd', ''))
        r['offset'] = next((float(str(a).split(':=')[1]) for a in ri.get('cmd', []) if str(a).startswith('start_offset:=')), None)
    except Exception:
        r['status'] = 'no_info'
    lg = next((f for f in (f'{rd}/launch.log', f'{rd}/launch.log.gz') if os.path.isfile(f)), None)
    last = None
    if lg:
        for line in opn(lg):
            if 'FINAL:' in line:
                last = line
            elif 'seconds total' in line:
                r['frames'] += 1
            elif 'SAVIOR-GATE' in line:
                g = GATE.search(line)
                if g:
                    r['gate'].append((g[1], float(g[9]), int(g[3]) + int(g[4]) + int(g[5]), int(g[6]) + int(g[7]) + int(g[8])))
    if r['savior']:
        g = FIN.search(last) if last else None
        if g:
            r.update(final='ok', fb=int(g[3]) + int(g[4]), late=int(g[5]))
    else:
        r['final'] = 'n/a'
    fs = f'{rd}/feature_stats.csv'
    if os.path.isfile(fs):
        with open(fs) as fh:
            r['in_core'] = sum(int(x.get('n_in_core') or 0) for x in csv.DictReader(fh))
    tc = f'{rd}/timing.csv'
    if os.path.isfile(tc):   # VINS-Fusion: stereo pairs received by vins_node (rw_analyze A5)
        r['frames'] = sum(1 for x in csv.DictReader(open(tc)) if x.get('kind') == 'frontend')
    return r


def audit(ds, seq, mdir, label, own):
    D = DATASETS[ds]
    out = []
    refd = f"{D['ref_root']}/{seq}/{D['ref_openvins']}"
    for rd in sorted(glob.glob(f'{mdir}/run_*')):
        run = os.path.basename(rd)
        i = int(run[4:])
        r = scan(rd)
        t = stamps(f'{rd}/stamped_traj_estimate.txt')
        o = stamps(f'{refd}/{run}/stamped_traj_estimate.txt')
        r.update(dataset=ds, seq=seq, method=label, run=run, own=int(own), poses=len(t), ref_poses=len(o), md5=md5(f'{rd}/stamped_traj_estimate.txt'))
        base_ok = r['status'].startswith('ok') and len(t) > 0 and r['final'] in ('ok', 'n/a') and r['fb'] + r['late'] == 0 and r['in_core'] == 0
        r['pose_ok'] = int(len(o) > 0 and len(t) >= len(o) - 1)
        if ds == 'monado':
            sota = label == 'vins_fusion'
            r['expected'] = EXP[seq]['ros1_pairs' if sota else 'ros2_pairs'][f'{0.2 * (i - 1):.1f}']
            r['frames_ok'] = int(r['frames'] == r['expected'])
            r['sync_ok'] = int(base_ok)
            r['end_ok'] = ''
            r['valid'] = int(base_ok and (sota or r['pose_ok']) and r['frames_ok'])
        else:
            r['sync_ok'] = int(r['status'] == 'ok/0' and base_ok)
            miss = (len(o) - sum(1 for x in o if x < t[0] - 1e-6) - len(t)) if t and o else 99
            r['end_ok'] = int(bool(t) and bool(o) and t[-1] >= o[-1] - 0.101 and miss <= 1)
            r['expected'] = r['frames_ok'] = ''
            r['valid'] = int(r['sync_ok'] and r['end_ok'])
        g = r.pop('gate')
        for f in ('msckf', 'slam'):
            lam = sorted(x[1] for x in g if x[0] == f)
            r[f'n_{f}'] = len(lam)
            r[f'lam_med_{f}'] = (lam[len(lam) // 2] if len(lam) % 2 else 0.5 * (lam[len(lam) // 2 - 1] + lam[len(lam) // 2])) if lam else ''
            r[f'lam_lo_{f}'] = sum(x <= LO + 1e-4 for x in lam) / len(lam) if lam else ''
            r[f'lam_hi_{f}'] = sum(x >= HI - 1e-4 for x in lam) / len(lam) if lam else ''
            last = [x for x in g if x[0] == f]
            r[f'rej_frac_{f}'] = (last[-1][3] / last[-1][2]) if last and last[-1][2] else ''
        out.append(r)
    return out


rows = []
for ds, D in DATASETS.items():
    for seq in D['seqs']:
        for v in VARIANTS:
            rows += audit(ds, seq, run_dir(ds, v, seq), v, True)
        for b in D['baselines']:
            rows += audit(ds, seq, baseline_dir(ds, b, seq), b, False)
# md5-identity controls (warehouse hall_t2_L3, SG install, flags off)
ctl = []
for v, b in (('ctl_sens_fix1', 'sens_fix1'), ('ctl_openvins', 'openvins')):
    for rd in sorted(glob.glob(f'{NV}/runs/ctl/hall_t2_L3/{v}/run_*')):
        ref = f"{R}/backend_v2/heldout/runs/hall_t2_L3/{b}/{os.path.basename(rd)}/stamped_traj_estimate.txt"
        ctl.append((v, os.path.basename(rd), int(md5(f'{rd}/stamped_traj_estimate.txt') == md5(ref) != '')))
os.makedirs(T, exist_ok=True)
keys = ['dataset', 'seq', 'method', 'run', 'own', 'offset', 'valid', 'sync_ok', 'end_ok', 'pose_ok', 'frames_ok', 'status', 'poses', 'ref_poses',
        'frames', 'expected', 'final', 'fb', 'late', 'in_core', 'savior', 'md5'] + [f'{k}_{f}' for f in ('msckf', 'slam') for k in ('n', 'lam_med', 'lam_lo', 'lam_hi', 'rej_frac')]
with open(f'{T}/audit.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
L = ['# NIS validation: validity audit (nv_audit.py)\n',
     'warehouse t2 / VIODE / OpenLORIS+uHumans2: rr_audit.py rules (clean exit, trajectory, FINAL fallbacks = late = 0, n_in_core = 0, '
     'end within 0.101 s of the same-offset OpenVINS(-v2) run, <= 1 pose missing). Monado: rw_analyze.py rules (+ pose rule, + frame rule +-0).\n',
     '| dataset | method | own | runs | valid | sync ok | end ok | pose rule ok | frame rule ok | fallbacks | late | n_in_core |', '|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|']
agg = {}
for r in rows:
    a = agg.setdefault((r['dataset'], r['method'], r['own']), dict(n=0, v=0, s=0, e=0, p=0, f=0, fb=0, late=0, core=0))
    a['n'] += 1; a['v'] += r['valid']; a['s'] += r['sync_ok']; a['e'] += r['end_ok'] or 0; a['p'] += r['pose_ok']; a['f'] += r['frames_ok'] or 0
    a['fb'] += r['fb']; a['late'] += r['late']; a['core'] += r['in_core']
for (ds, m, own), a in agg.items():
    L.append(f"| {ds} | {m} | {'yes' if own else 'baseline'} | {a['n']} | {a['v']} | {a['s']} | {a['e'] if ds != 'monado' else '-'} | {a['p']} | "
             f"{a['f'] if ds == 'monado' else '-'} | {a['fb']} | {a['late']} | {a['core']} |")
bad = [r for r in rows if not r['valid']]
L += ['\n## Invalid runs\n', '| dataset | seq | method | run | status | poses | ref poses | frames / expected | FINAL | fb | late | in core | end ok |',
      '|---|---|---|---|---|--:|--:|---|---|--:|--:|--:|--:|']
L += [f"| {r['dataset']} | {r['seq']} | {r['method']} | {r['run']} | {r['status']} | {r['poses']} | {r['ref_poses']} | {r['frames']} / {r['expected']} | "
      f"{r['final']} | {r['fb']} | {r['late']} | {r['in_core']} | {r['end_ok']} |" for r in bad]
L += ['\n## md5-identity controls (SG install, flags off, hall_t2_L3 runs 1-5 vs frozen back-end v2 held-out runs)\n']
for v in ('ctl_sens_fix1', 'ctl_openvins'):
    c = [x for x in ctl if x[0] == v]
    L.append(f'- {v}: {sum(x[2] for x in c)} / {len(c)} byte-identical')
open(f'{T}/audit.md', 'w').write('\n'.join(L) + '\n')
SET = {'warehouse_t2': 't2', 'viode': 'viode', 'openloris_uhumans2': 'e', 'monado': 'rw'}
open(f'{T}/invalid.txt', 'w').write(''.join(f"{SET[r['dataset']]} {r['seq']} {r['method']} {r['run']}\n" for r in bad if r['own']))
open(f'{T}/invalid_baselines.txt', 'w').write(''.join(f"{r['dataset']} {r['seq']} {r['method']} {r['run']}\n" for r in bad if not r['own']))
print('\n'.join(L[:4 + len(agg)])); print(f'invalid own: {sum(1 for r in bad if r["own"])}, baselines: {sum(1 for r in bad if not r["own"])}')
