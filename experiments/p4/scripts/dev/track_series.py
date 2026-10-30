import json, sys
rows = [json.loads(l) for l in open(sys.argv[1])]
tid = int(sys.argv[2]); step = int(sys.argv[3]) if len(sys.argv) > 3 else 5
for r in rows[::1]:
    for i in r['instances']:
        mo = i.get('motion')
        if mo and mo['id'] == tid and r['frame'] % step == 0:
            m = r.get('motion', {})
            print(r['frame'], i['status'], 'z=%.2f' % (i['depth'] or -1), 'bbox', i['bbox'], {k: mo.get(k) for k in ('obs', 'l', 'v_lat', 's_lat', 'v_rad', 's_rad', 'ema_lat', 'ema_s', 'ema_rad', 'n')}, 't', m.get('t'))
