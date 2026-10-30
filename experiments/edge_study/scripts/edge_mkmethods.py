"""edge_mkmethods.py: closed-loop EDGE methods -> edge_methods.json {name: {roles, pset, ov, model}}.
pset = MAIN (frozen sens_fix1) + the perception variant's overrides (edge_variants.py) + node-only keys; ov = extra
ov_set keys (idea 3: simulated mask latency / deferred invalidation)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edge_variants import MAIN, VARIANTS, BASES
WS = '/home/sasa/workspace/savior_ws'
SCR = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge'
ENG = {'s672': WS + '/models/warehouse/yolo26s-seg-warehouse.engine'}
for m in ('n672', 's512', 'n512', 's416', 'n416', 's672i8', 'n672i8', 's512i8', 'n512i8'):
    ENG[m] = f'{SCR}/engines/{m}.engine'
M = {}
def add(name, var='main', ov='', extra=None):
    spec = VARIANTS[var]
    o = {**BASES[spec.get('base', 'main')], **spec.get('over', {}), **(extra or {})}
    o['segmenter.fast_masks'] = True
    if spec.get('det', 's672') != 's672':
        o['segmenter.imgsz'] = int(spec['det'][1:4])      # engine input size (as detcache_edge.py)
    o['stats_compact'] = True
    M[name] = {'roles': spec.get('roles', 'warehouse'), 'var': var,
               'pset': ' '.join(f'{k}={str(v).lower() if isinstance(v, bool) else v}' for k, v in sorted(o.items())),
               'ov': ov, 'model': ENG[spec.get('det', 's672')]}
add('e_main')                                   # control: must equal p7 sens_fix1 (md5)
for v in VARIANTS:
    if v != 'main':
        add('e_' + v, v)
# idea 3: simulated mask latency L (sensor time); stale = newest arrived mask only; dfr = + deferred invalidation
for L in (100, 250, 500):
    add(f'e_L{L}_stale', ov=f'dynamic_mask_sim_latency_ms={float(L)}')
    add(f'e_L{L}_dfr', ov=f'dynamic_mask_sim_latency_ms={float(L)} dynamic_mask_deferred=true')
    add(f'e_L{L}_dfronly', ov=f'dynamic_mask_sim_latency_ms={float(L)} dynamic_mask_deferred=true dynamic_mask_stale_gating=false')
# combinations of idea 2/1 with idea 3 (perception output additionally L ms late at OpenVINS, deferred invalidation)
add('e_c_sp_r10_L50_dfr100', 'c_sp_r10_L50', ov='dynamic_mask_sim_latency_ms=100.0 dynamic_mask_deferred=true')
add('e_c_sp_r10_dfr100', 'c_sp_r10', ov='dynamic_mask_sim_latency_ms=100.0 dynamic_mask_deferred=true')
add('e_c_n672_L100stale', 'c_n672_L100', ov='dynamic_mask_sim_latency_ms=100.0')
add('e_c_n672_L250dfronly', 'c_n672_L100', ov='dynamic_mask_sim_latency_ms=250.0 dynamic_mask_deferred=true dynamic_mask_stale_gating=false')
json.dump(M, open(f'{SCR}/edge_methods.json', 'w'), indent=1, sort_keys=True)
print(len(M), 'methods')
