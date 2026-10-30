import sys, math, numpy as np
VV=sys.argv[1] if len(sys.argv)>1 else 'sp'; sys.argv=['x']; __file__='/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge/scripts/edgeeval.py'
exec(open('/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge/scripts/edgeeval.py').read().split("def main():")[0])
from savior_perception.core.types import Instance
seq='hall_t1_L2'
ref,_,rect=make_pipe(MAIN,'warehouse'); var,_,_=make_pipe({**MAIN,**VARIANTS[VV]['over']},'warehouse')
g,frames=load_frames(seq); dc=DetCache(CACHES['s672']+f'/{seq}.npz')
stamps=sorted(frames)[:400]; prev=None
rows=[]
for k,st in enumerate(stamps):
    l,r=frames[st]; t=st*1e-9; R=g.rotation(prev,t) if prev else None; prev=t
    ref.process(l,r,t,dc.get(st,Instance),R_imu=R); var.process(l,r,t,dc.get(st,Instance),R_imu=R)
    if k%20==0 and k>0:
        for a,b in zip(ref.last_result.instances,var.last_result.instances):
            if a.role in('dynamic','potential') and a.status!='carried':
                x0,y0,x1,y1=a.bbox
                rows.append((a.cls,min(x1-x0,y1-y0),a.depth,a.n_depth_px,b.depth,b.n_depth_px))
import collections
for r_ in rows[:60]: print(r_)
rows=np.array([(r_[1],r_[2],r_[4],r_[5]) for r_ in rows],float)
print('n',len(rows),'ref ok',np.isfinite(rows[:,1]).mean(),'var ok',np.isfinite(rows[:,2]).mean())
for lo,hi in ((0,15),(15,30),(30,60),(60,1000)):
    s=(rows[:,0]>=lo)&(rows[:,0]<hi); print(lo,hi,s.sum(),'ref',np.isfinite(rows[s,1]).mean(),'var',np.isfinite(rows[s,2]).mean())
z=rows[:,1]; ok=np.isfinite(z)
for lo,hi in ((0,1.5),(1.5,3),(3,6),(6,100)):
    s=ok&(z>=lo)&(z<hi); print('z',lo,hi,s.sum(),'var',np.isfinite(rows[s,2]).mean() if s.sum() else 0, np.nanmedian(np.abs(rows[s,2]-z[s])/z[s]) if s.sum() else 0)
