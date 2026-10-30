#!/usr/bin/env python3
"""edgeprof.py <variant> <seq> <n_frames> [out.json]: cProfile of the pipeline (detections from the cache, 1 thread) ->
per-stage split into native (OpenCV / numpy / C builtins: tottime of built-in functions) vs Python glue (tottime of Python
functions) for each top-level stage function; also the wall time per stage without the profiler (second pass)."""
import cProfile, json, math, os, pstats, sys, time
__file__ = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge/scripts/edgeeval.py'
V, SEQ, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
OUT = sys.argv[4] if len(sys.argv) > 4 else None
sys.argv = ['x']
exec(open(__file__).read().split("def main():")[0])
from savior_perception.core.types import Instance
from savior_perception.core.asyncseg import AsyncSegDriver
spec = VARIANTS[V]
pipe, cfg, rect = make_pipe({**MAIN, **spec.get('over', {})}, spec.get('roles', 'warehouse'))
g, frames = load_frames(SEQ)
dc = DetCache(CACHES[spec.get('det', 's672')] + f'/{SEQ}.npz')
stamps = sorted(s for s in frames if frames[s][0] is not None and frames[s][1] is not None)[:N]
dets = {st: dc.get(st, Instance) for st in stamps}
def run(p, prof=None):
    prev = None
    tim = {}
    drv = AsyncSegDriver(p, cfg.asyncseg, rect, g.rotation) if cfg.asyncseg.enable else None
    for st in stamps:
        l, r = frames[st]
        t = st * 1e-9
        R = g.rotation(prev, t) if prev else None
        prev = t
        insts = [Instance(mask=x.mask.copy(), cls=x.cls, score=x.score, bbox=x.bbox) for x in dets[st]]
        if prof: prof.enable()
        c0 = time.perf_counter()
        if drv is not None:
            if drv.is_key(t):
                st_ = drv.process_key(l, r, t, insts, drv.key_rotation(t))
                for k, v in st_['timings_ms'].items():
                    tim.setdefault(k, []).append(v)
            drv.output(t, l.shape[:2], r.shape[:2])
        else:
            _, _, st_ = p.process(l, r, t, insts, R_imu=R)
            for k, v in st_['timings_ms'].items():
                tim.setdefault(k, []).append(v)
        tim.setdefault('frame', []).append((time.perf_counter() - c0) * 1e3)
        if prof: prof.disable()
    return tim
tim = run(pipe)                                      # wall (no profiler)
pipe2, _, _ = make_pipe({**MAIN, **spec.get('over', {})}, spec.get('roles', 'warehouse'))
pr = cProfile.Profile()
run(pipe2, pr)
st = pstats.Stats(pr)
if OUT:
    pr.dump_stats(OUT.replace('.json', '.pstats'))
# native (C) tottime attributed to the SAVIOR source file that (transitively, through numpy / cv2 python wrappers)
# called it: file -> stage; python tottime of SAVIOR files -> stage. Python share per stage = stage wall - native.
FILE_STAGE = {'stereo_depth.py': 'depth', 'motion.py': 'motion', 'selective.py': 'motion', 'gating.py': 'gating',
              'tracker.py': 'tracking', 'compose.py': 'compose', 'extension.py': 'extension', 'asyncseg.py': 'predict',
              'pipeline.py': 'glue', 'types.py': 'glue', 'calibration.py': 'glue'}
def stage_of(fk):
    import os as _o
    return FILE_STAGE.get(_o.path.basename(fk[0])) if 'savior_perception' in fk[0] else None
def attribute(fk, w, depth=0):
    sg = stage_of(fk)
    if sg is not None:
        return {sg: w}
    if depth > 6:
        return {'other': w}
    callers = st.stats[fk][4]
    tot = sum(v[3] for v in callers.values()) or sum(v[2] for v in callers.values())
    out = {}
    if not callers or tot <= 0:
        return {'other': w}
    for ck, v in callers.items():
        share = (v[3] if sum(x[3] for x in callers.values()) > 0 else v[2]) / tot
        for k, x in attribute(ck, w * share, depth + 1).items():
            out[k] = out.get(k, 0.0) + x
    return out
nat_stage, py_stage = {}, {}
for fk, (cc, nc, tt, ct, callers) in st.stats.items():
    native = fk[0] == '~' or fk[0].startswith('<')
    if native:
        for k, x in attribute(fk, tt).items():
            nat_stage[k] = nat_stage.get(k, 0.0) + x
    else:
        sg = stage_of(fk)
        if sg is not None:
            py_stage[sg] = py_stage.get(sg, 0.0) + tt
# attribute every function's tottime to its stage by walking the callers graph is costly; instead: per stage entry
# function, cumulative time, and the total native vs python tottime split over everything.
nat = py = 0.0
per_file = {}
for (fn, ln, name), (cc, nc, tt, ct, callers) in st.stats.items():
    native = fn == '~' or fn.startswith('<')
    if native:
        nat += tt
    else:
        py += tt
    key = ('native:' + name) if native else (os.path.basename(fn) + ':' + name)
    per_file[key] = per_file.get(key, 0.0) + tt
# per-stage python/native split: profile each stage's subtree via the 'cumulative' of entry points
ENTRY = {'depth': ('stereo_depth.py', 'compute'), 'motion': ('motion.py', 'update'), 'gating': ('gating.py', 'run'),
         'tracking': ('tracker.py', 'update'), 'compose_left': ('compose.py', 'compose_left'), 'right_warp': ('compose.py', 'warp'),
         'selective': ('selective.py', 'update'), 'process': ('pipeline.py', 'process')}
cum = {}
for (fn, ln, name), (cc, nc, tt, ct, callers) in st.stats.items():
    for k, (f_, n_) in ENTRY.items():
        if fn.endswith(f_) and name == n_:
            cum[k] = cum.get(k, 0.0) + ct
# subtree native share per stage: run a separate profile restricted to each entry with pstats' callees is complex; use
# the 'print_callees' tree flattened (one level of recursion is enough for the hot paths)
def subtree(fkey, seen=None, depth=0):
    seen = seen or set()
    if fkey in seen or depth > 40:
        return 0.0, 0.0
    seen.add(fkey)
    cc, nc, tt, ct, callers = st.stats[fkey]
    native = fkey[0] == '~' or fkey[0].startswith('<')
    n_, p_ = (tt, 0.0) if native else (0.0, tt)
    for callee, (ccc, cnc, ctt, cct, ccallers) in st.stats.items():
        if fkey in ccallers:
            frac = ccallers[fkey][3] / cct if cct > 0 else 0.0   # share of the callee's cumulative time from this caller
            a, b = subtree(callee, seen, depth + 1)
            n_ += a * frac
            p_ += b * frac
    return n_, p_
split = {}
for k, (f_, n_) in ENTRY.items():
    keys = [fk for fk in st.stats if fk[0].endswith(f_) and fk[2] == n_]
    if keys:
        a, b = subtree(keys[0])
        split[k] = {'native_ms_per_frame': 1e3 * a / len(stamps), 'python_ms_per_frame': 1e3 * b / len(stamps)}
top = sorted(per_file.items(), key=lambda kv: -kv[1])[:40]
res = {'variant': V, 'seq': SEQ, 'frames': len(stamps),
       'wall_ms': {k: [float(np.median(v)), float(np.percentile(v, 90)), float(np.mean(v))] for k, v in tim.items()},
       'prof_total_native_ms_per_frame': 1e3 * nat / len(stamps), 'prof_total_python_ms_per_frame': 1e3 * py / len(stamps),
       'stage_split': split,
       'native_by_stage_ms_per_frame': {k: 1e3 * v / len(stamps) for k, v in nat_stage.items()},
       'python_by_stage_ms_per_frame_profiled': {k: 1e3 * v / len(stamps) for k, v in py_stage.items()}, 'top_tottime_ms_per_frame': [(k, 1e3 * v / len(stamps)) for k, v in top]}
print(json.dumps(res, indent=1))
if OUT:
    json.dump(res, open(OUT, 'w'), indent=1)
