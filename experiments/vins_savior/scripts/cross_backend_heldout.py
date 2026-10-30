import json, numpy as np, sys
R='/ws/results/'
for ds, gs, fail in (('t2', {'L0+L1':['L0','L1'],'L2+L3':['L2','L3'],'all':['L0','L1','L2','L3']}, 2.0),
                     ('viode', {'none+low':['none','low'],'mid+high':['mid','high'],'all':['none','low','mid','high']}, 1.0)):
    a=json.load(open(R+f'vins_savior/heldout/tables_{ds}/ate.json'))['values']
    b=json.load(open(R+f'backend_v2/tables/ate_{ds}.json'))['values']['v2']
    if ds=='t2': print('keys', list(a)[:2], list(b)[:2], list(a[list(a)[0]]))
    M={'OV2':(b,'openvins'),'OV2+SAVIOR':(b,'sens_fix1'),'OV2+Y-Cls':(b,'yolo_naive'),'VINS':(a,'vins_fusion'),'VINS+SAVIOR':(a,'vins_savior'),'DynaVINS':(a,'dynavins')}
    for g,lv in gs.items():
        V={}
        for n,(src,m) in M.items():
            V[n]={(s,k):min(v,10.0) for s,d in src.items() if s.split('_')[-1] in lv for k,v in d[m].items()}
        print(f'== {ds} {g}')
        for n,v in V.items():
            x=np.array(list(v.values())); print(f'  {n:12s} gm={np.exp(np.mean(np.log(x))):.3f} med={np.median(x):.3f} fail={int((x>fail).sum())}/{len(x)}')
        for x,y in [('OV2+SAVIOR','DynaVINS'),('OV2+SAVIOR','VINS+SAVIOR'),('OV2','VINS'),('OV2+SAVIOR','VINS')]:
            k=sorted(set(V[x])&set(V[y])); r=np.log([V[x][i] for i in k])-np.log([V[y][i] for i in k])
            bs=[np.exp(np.random.default_rng(i).choice(r,len(r)).mean())-1 for i in range(2000)]
            from scipy.stats import wilcoxon
            p=wilcoxon(r).pvalue if np.any(r!=0) else 1
            print(f'  {x} vs {y}: {100*(np.exp(r.mean())-1):+.1f}% [{100*np.percentile(bs,2.5):+.0f},{100*np.percentile(bs,97.5):+.0f}] p={p:.2g} wins {int((r<0).sum())}/{len(r)}')
