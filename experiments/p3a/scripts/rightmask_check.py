"""Person instances without stereo depth (-> no right-mask polygon) in savior_node stats of oracle_person runs."""
import glob, json, sys
import numpy as np
for fn in sorted(glob.glob(sys.argv[1])):
    n = nd = nd_edge = 0; area_nd = []; area_all = []
    for l in open(fn):
        r = json.loads(l)
        for i in r['instances']:
            if i['cls'] != 'person': continue
            x0, y0, x1, y1 = i['bbox']; a = (x1 - x0) * (y1 - y0)
            n += 1; area_all.append(a)
            if i['depth'] is None:
                nd += 1; area_nd.append(a)
                if x0 <= 25: nd_edge += 1     # left-image left border: not visible in the right camera at d <= 25 px
    print(fn.split('/')[-4], fn.split('/')[-2], f'person inst {n}, no depth {nd} ({100*nd/max(1,n):.1f} %), of which at left border {nd_edge};'
          f' median bbox area no-depth {np.median(area_nd) if area_nd else 0:.0f} px vs all {np.median(area_all):.0f} px')
