import json, sys, numpy as np
from collections import Counter
rows=[json.loads(l) for l in open(sys.argv[1])]
keys=['segment','depth','gating','tracking','extension','compose','total']
for k in keys:
    v=np.array([r['timings_ms'][k] for r in rows]); print(k, 'med %.2f p90 %.2f max %.1f'%(np.median(v),np.percentile(v,90),v.max()))
npers=np.array([r['n_by_role']['dynamic'] for r in rows]); npot=np.array([r['n_by_role']['potential'] for r in rows])
print('frames',len(rows),'persons/frame mean %.2f'%npers.mean(),'frames with person %.2f'%(npers>0).mean(),'max',npers.max())
print('potential mean %.2f'%npot.mean(), 'promoted mean %.2f'%np.mean([r['n_promoted'] for r in rows]), 'carried mean %.2f'%np.mean([r['n_carried'] for r in rows]))
print('core frac mean %.4f'%(np.mean([r['core_px'] for r in rows])/(848*800)), 'ext %.4f'%(np.mean([r['ext_px'] for r in rows])/(848*800)), 'right core %.4f'%(np.mean([r.get('right_core_px',0) for r in rows])/(848*800)))
c=Counter()
for r in rows:
    for i in r['instances']: c[(i['cls'],i['status'])]+=1
print(c.most_common(20))
dep=[i['depth'] for r in rows for i in r['instances'] if i['cls']=='person' and i['depth']]
nod=[1 for r in rows for i in r['instances'] if i['cls']=='person' and not i['depth']]
print('person depth: n=%d med %.2f p10 %.2f p90 %.2f, unknown %d'%(len(dep),np.median(dep),np.percentile(dep,10),np.percentile(dep,90),len(nod)))
