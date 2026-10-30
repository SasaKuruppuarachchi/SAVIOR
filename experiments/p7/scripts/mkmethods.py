"""mkmethods.py: results/p7/methods.json (online method -> roles + pset) from variants.py VARIANTS + sweeps/online.json.
Node-only keys (segmenter.fast_masks, stats_compact) are added to every YOLO method (no effect on the masks)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from variants import VARIANTS
D = os.path.dirname(os.path.abspath(__file__))
V = dict(VARIANTS)
import glob
for extra in sorted(glob.glob(f'{D}/sweeps/online*.json')):   # online.json (stage E), online_timing.json (stage F)
    V.update({k: tuple(v) for k, v in json.load(open(extra)).items()})
out = {}
for name, (src, roles, over) in V.items():
    if src != 'wh':
        continue
    o = dict(over)
    o.setdefault('segmenter.fast_masks', True)
    o['stats_compact'] = True
    out[name] = {'roles': roles, 'pset': ' '.join(f'{k}={str(v).lower() if isinstance(v, bool) else v}' for k, v in sorted(o.items()))}
json.dump(out, open(f'{D}/../methods.json', 'w'), indent=1, sort_keys=True)
print('\n'.join(f'{k}: {v["roles"]} | {v["pset"]}' for k, v in sorted(out.items())))
