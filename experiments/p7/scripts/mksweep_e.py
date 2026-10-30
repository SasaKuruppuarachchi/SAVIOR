"""mksweep_e.py <main variant>: stage E sensitivity variants on the chosen main (-> sweeps/sens_e.json; used by p7eval.py
--extra-json offline and by mkmethods.py through sweeps/online.json for closed loop).
  sens_fix<d>  : paper dist_int: gating.mode=fixed, fixed_threshold_m=d, link_depth=median (the fixed threshold is only
                 used by the median-depth test; with link_depth=contact it would be inert)
  sens_k<k>    : adaptive gate of the main (link_depth=contact, margin 0.30 + min(k*sigma, max_noise 0.5)), k_sigma=k
  sens_kmed<k> : adaptive median-depth gate |dz| < size prior + k*sigma (size prior default, noise cap 0.5), offline only"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from variants import VARIANTS
main = sys.argv[1]
src, roles, base = VARIANTS[main]
out = {}
for d in (0, 1, 2, 3, 4):
    out[f'sens_fix{d}'] = [src, roles, {**base, 'gating.mode': 'fixed', 'gating.fixed_threshold_m': float(d), 'gating.link_depth': 'median'}]
for k in (1, 2, 3, 4):
    out[f'sens_k{k}'] = [src, roles, {**base, 'gating.k_sigma': float(k)}]
    out[f'sens_kmed{k}'] = [src, roles, {**base, 'gating.k_sigma': float(k), 'gating.link_depth': 'median'}]
D = os.path.dirname(os.path.abspath(__file__))
json.dump(out, open(f'{D}/sweeps/sens_e.json', 'w'), indent=1)
print(' '.join(out))
