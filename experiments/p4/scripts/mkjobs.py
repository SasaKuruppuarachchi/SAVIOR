import os, sys, subprocess
R = '/home/sasa/workspace/savior_ws/results/p4'
running = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True).stdout.split()
def need(ds, seq, m):
    d = '%s/%s_%s/%s' % (R, ds, seq, m)
    n = len([x for x in os.listdir(d) if x.startswith('run_')]) if os.path.isdir(d) else 0
    name = 'agentH_%s_%s_' % (m.replace('+', '_'), seq)
    return n < 5 and not any(r.startswith(name) for r in running)
HO = ['cafe1-2'] + ['office1-%d' % i for i in range(1, 8)]
ol, uh = [], []
for m in ['full+mot+gate', 'full+mot', 'full+mot+noprom+noveto+gate', 'full+mot+gate+noext', 'full+mot+gate+icore',
          'full+mot+gate+band', 'full+mot+gate+trk', 'full+mot+gate+trkego', 'full+trk']:
    ol.append(('openloris', 'cafe1-1', m))
for s in HO:
    for m in ['openvins', 'none', 'full', 'full+mot+gate', 'full+mot', 'full+gate', 'full+mot+noprom+noveto+gate', 'openvins+fast15']:
        ol.append(('openloris', s, m))
for s, ms in [('office_s1_06h', ['full+mot+gate', 'full+mot']), ('office_s1_12h', ['openvins', 'full', 'full+mot+gate', 'none']),
              ('office_s1_00h', ['openvins', 'full', 'full+mot+gate', 'none'])]:
    for m in ms:
        uh.append(('uhumans2', s, m))
open(sys.argv[1], 'w').write(''.join('%s %s %s\n' % j for j in ol if need(*j)))
open(sys.argv[2], 'w').write(''.join('%s %s %s\n' % j for j in uh if need(*j)))
