import json, numpy as np
R='/ws/results/'
a=json.load(open(R+'vins_savior/tables/ate.json'))['values']
b=json.load(open(R+'backend_v2/tables/ate_t1.json'))['values']['v2']
G={'L0+L1':['L0','L1'],'L2+L3':['L2','L3'],'hall_L3':None}
def vals(src,m,g):
    o={}
    for s,d in src.items():
        lv=s.split('_')[-1]
        if (g=='hall_L3' and s=='hall_t1_L3') or (g!='hall_L3' and lv in G[g]):
            for k,v in d[m].items(): o[(s,k)]=v
    return o
M={'OV2':(b,'openvins'),'OV2+SAVIOR':(b,'sens_fix1'),'OV2+Y-Cls':(b,'yolo_naive'),'VINS':(a,'vins_fusion'),'VINS+SAVIOR':(a,'vins_savior'),'DynaVINS':(a,'dynavins')}
for g in G:
    print('==',g)
    V={n:vals(s,m,g) for n,(s,m) in M.items()}
    for n,v in V.items(): print(f'  {n:12s} gm={np.exp(np.mean(np.log(list(v.values())))):.3f} med={np.median(list(v.values())):.3f} n={len(v)}')
    for x,y in [('OV2+SAVIOR','DynaVINS'),('OV2+SAVIOR','VINS+SAVIOR'),('OV2','VINS')]:
        k=sorted(set(V[x])&set(V[y])); r=np.log([V[x][i] for i in k])-np.log([V[y][i] for i in k])
        bs=[np.exp(np.random.default_rng(i).choice(r,len(r)).mean())-1 for i in range(2000)]
        print(f'  {x} vs {y}: {100*(np.exp(r.mean())-1):+.1f}% [{100*np.percentile(bs,2.5):+.0f},{100*np.percentile(bs,97.5):+.0f}] wins {int((r<0).sum())}/{len(r)}')
