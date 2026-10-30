import json, sys, glob, os, numpy as np
from collections import defaultdict
D = sys.argv[1]
print('| sequence | variant | frames w/ person | core % | band % | person-frames root / still / other | person area still % | chair promoted+root area % | chair promoted (frames) | motion ms (wall, loaded) |')
print('|:--|:--|--:|--:|--:|:--|--:|--:|--:|--:|')
for seq in ['cafe1-1', 'cafe1-2', 'office1-5', 'office1-7', 'office_s1_06h', 'office_s1_12h']:
    for var in sys.argv[2].split(','):
        fn = '%s/%s_%s.jsonl' % (D, var, seq)
        if not os.path.isfile(fn): continue
        rows = [json.loads(l) for l in open(fn)]
        npx = rows[0]['image_size'][0] * rows[0]['image_size'][1]
        c = defaultdict(int); A = defaultdict(float); fp = 0
        for r in rows:
            hasp = False
            for i in r['instances']:
                if i['cls'] == 'person':
                    hasp = True; c[i['status']] += 1; A['p_' + i['status']] += i.get('area', 0)
                elif i['role'] == 'potential':
                    A['c_' + i['status']] += i.get('area', 0)
                    if i['status'] in ('promoted', 'root'): c['chair_dyn'] += 1
            fp += hasp
        pa = sum(v for k, v in A.items() if k.startswith('p_'))
        mo = [r['timings_ms'].get('motion') for r in rows if 'motion' in r['timings_ms']]
        print('| %s | %s | %d/%d | %.2f | %.2f | %d / %d / %d | %.0f | %.2f | %d | %s |' % (seq, var, fp, len(rows),
              100 * np.mean([r['core_px'] for r in rows]) / npx, 100 * np.mean([r['ext_px'] for r in rows]) / npx,
              c['root'], c['still'], sum(v for k, v in c.items() if k not in ('root', 'still', 'chair_dyn')),
              100 * A['p_still'] / max(pa, 1), 100 * (A['c_promoted'] + A['c_root']) / (len(rows) * npx), c['chair_dyn'],
              ('%.1f' % np.median(mo)) if mo else '–'))
