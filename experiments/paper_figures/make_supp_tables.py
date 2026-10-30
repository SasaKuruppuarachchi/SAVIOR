import json
R='/home/sasa/workspace/savior_ws/results'
K={d['claim']:d for d in json.load(open(R+'/stats_v3/tables/key_effects.json'))}
G={'L0+L1':'static+low','L2+L3':'medium+heavy','L0':'static','none+low':'none+low','mid+high':'mid+high','all':'all'}
rows=[('C2',r'\odyn+B vs.\ \ocls+B'),('C3',r'\odyn+B vs.\ \ocls+B'),('C4b',r'VINS+\odyn+B vs.\ VINS+\ocls+B'),
('C6',r'SAVIOR vs.\ \ycls'),('C7',r'SAVIOR vs.\ \ycls'),('C8a',r'VINS+SAVIOR vs.\ VINS+\ycls'),('C8b',r'VINS+SAVIOR vs.\ VINS+\ycls'),
('C10',r'\ycls{} vs.\ \ov'),('C11',r'\ocls+B vs.\ \ov'),('C1',r'\odyn+B vs.\ \ov'),('C15',r'SAVIOR vs.\ \ov'),
('C16',r'VINS+SAVIOR vs.\ VINS-Fusion'),('C17',r'VINS+\ycls{} vs.\ VINS-Fusion'),('C23',r'SAVIOR-edge vs.\ SAVIOR'),
('C22',r'\ov+SAVIOR vs.\ DynaVINS'),
('C5b',r'\odyn+B vs.\ \ocls+B'),('C9b',r'SAVIOR vs.\ \ycls'),('C19',r'VINS+SAVIOR vs.\ VINS-Fusion'),
('C20',r'\ov+SAVIOR vs.\ DynaVINS'),('C21',r'\ov+SAVIOR vs.\ VINS-Fusion')]
def f(x): return ('$%+d$'%round(x)) if round(x)<0 else '$+%d$'%round(x)
def p(x): return '%.3f'%x if x>=0.001 else '%.0e'%x
o=[]
o.append(r'\begin{tabular}{l l c r l c l c c}')
o.append(r'\toprule')
o.append(r'Comparison & Group & $k$ & Effect [\%] & Mixed-model 95\,\% CI & Seq.\ better/worse & $p$ / $p_\mathrm{H}$ & Fail.\ A / B & Non-failed [\%] \\')
o.append(r'\midrule')
sec=None
for c,l in rows:
    d=K[c]; s='warehouse' if d['ds']=='t2' else 'VIODE'
    if s!=sec:
        if sec: o.append(r'\midrule')
        o.append(r'\multicolumn{9}{l}{\emph{%s}}\\'%('Warehouse held-out split' if s=='warehouse' else 'VIODE')); sec=s
    ph=d['holm']['global_claims']['lmm']
    pp=p(d['p_lmm'])+' / '+('%.2f'%ph if ph>=0.1 else '%.3f'%ph)
    if ph<0.05: pp=r'\textbf{'+pp+'}'
    fa=d['fails']; 
    o.append(r'\quad %s & %s & %d & %s & [%s, %s] & %d/%d & %s & %s / %s & %s \\'%(l,G[d['group']],d['k'],f(d['est']),f(d['lmm_ci'][0]),f(d['lmm_ci'][1]),d['seq_better'],d['seq_worse'],pp,fa[0].split('/')[0],fa[1].split('/')[0],f(d['nonfailed']['est'])))
o.append(r'\bottomrule\end{tabular}')
open('tables/supp_seqlevel.tex','w').write('\n'.join(o)+'\n')
print('\n'.join(o))
