#!/usr/bin/env python3
"""p7condense.py <tag> <ref> [groups comma] : one line per method from tables/{ate,rpe}_<tag>.json (geometric-mean change,
95 % CI, Holm p, wins/losses) -> stdout and tables/summary_<tag>_vs_<ref>.md. Host python."""
import json, os, sys
T = '/home/sasa/workspace/savior_ws/results/p7/tables'
tag, ref = sys.argv[1], sys.argv[2]
G = sys.argv[3].split(',') if len(sys.argv) > 3 else ['L0', 'L0+L1', 'L2+L3', 'hall_L3']
L = [f'# {tag}: paired vs {ref} (geometric-mean ratio - 1 [95 % CI], Holm p, wins/losses)\n']
for met in ('ate', 'rpe'):
    fn = f'{T}/{met}_{tag}.json'
    if not os.path.isfile(fn):
        continue
    A = json.load(open(fn))
    ms = sorted({x['method'] for x in A['paired'] if x['ref'] == ref})
    L += [f'## {met.upper()}\n', '| method | ' + ' | '.join(G) + ' |', '|---|' + '---|' * len(G)]
    for m in ms:
        c = []
        for g in G:
            r = [x for x in A['paired'] if x['ref'] == ref and x['method'] == m and x['group'] == g]
            c.append(f"{r[0]['gm']:+.0f} % [{r[0]['ci'][0]:+.0f}, {r[0]['ci'][1]:+.0f}] H={r[0]['holm']:.3f} {r[0]['wins']}/{r[0]['losses']}" if r else '-')
        L.append(f'| {m} | ' + ' | '.join(c) + ' |')
    L.append('')
open(f'{T}/summary_{tag}_vs_{ref}.md', 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
