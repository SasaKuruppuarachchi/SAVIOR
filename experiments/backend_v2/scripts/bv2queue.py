#!/usr/bin/env python3
"""bv2queue.py <jobs file> <max parallel>: run 'seq method [offsets,comma|-] [start|-] [KEY=VAL ...]' lines with run_bv2.sh
(jobqueue.py of P7 with the bv2_ container prefix). Domains 20..219 recycled; '#' lines skipped. A job is skipped if its
method dir (results/<DSN>/...) already holds a non-empty run_XX/stamped_traj_estimate.txt for every requested index.
Caps: GLOBAL_MAX (default 12) on ALL containers named PREFIX* (default bv2_); RUNNER (default run_bv2.sh), QLOG; STAGGER_S (default 20 s) between container starts."""
import os, subprocess, sys, time
S = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/bv2'
WS = '/home/sasa/workspace/savior_ws'
D = os.path.dirname(os.path.abspath(__file__))
jobs = []
for l in open(sys.argv[1]):
    if not l.strip() or l.startswith('#'):
        continue
    p = l.split()
    seq, m = p[0], p[1]
    offs = p[2].split(',') if len(p) > 2 and p[2] != '-' else None
    start = int(p[3]) if len(p) > 3 and p[3] != '-' else 1
    env = dict(x.split('=', 1) for x in p[4:])
    R = f"{WS}/results/{env.get('DSN', os.environ.get('DSN', 'backend_v2/runs'))}"
    idx = range(start, start + (len(offs) if offs else 10))
    f = lambda i: f'{R}/{seq}/{m}/run_{i:02d}/stamped_traj_estimate.txt'
    if all(os.path.isfile(f(i)) and os.path.getsize(f(i)) > 0 for i in idx) and not env.get('FORCE'):
        continue
    jobs.append((seq, m, offs, start, env))
par = int(sys.argv[2])
free = list(range(int(os.environ.get('DOM_LO', '20')), int(os.environ.get('DOM_HI', '220'))))
STAGGER = float(os.environ.get('STAGGER_S', '20'))
GLOBAL_MAX = int(os.environ.get('GLOBAL_MAX', '12'))
PREFIX = os.environ.get('PREFIX', 'bv2_')   # container-name prefix counted against GLOBAL_MAX
RUNNER = os.environ.get('RUNNER', os.path.join(D, 'run_bv2.sh'))
last_start = 0.0
running = {}
os.makedirs(S + '/logs', exist_ok=True)
log = open(S + '/logs/' + os.environ.get('QLOG', 'queue.log'), 'a')
log.write('%s queue %s: %d jobs\n' % (time.strftime('%F %T'), sys.argv[1], len(jobs))); log.flush()
while jobs or running:
    for p in list(running):
        if p.poll() is not None:
            dom, j = running.pop(p)
            log.write('%s done %s %s %d rc=%s\n' % (time.strftime('%T'), j[0], j[1], j[3], p.returncode)); log.flush()
            free.append(dom)
    nglob = int(subprocess.run("docker ps --format '{{.Names}}' | grep -c '^%s'" % PREFIX, shell=True, capture_output=True, text=True).stdout.strip() or 0)
    while jobs and len(running) < par and time.time() - last_start >= STAGGER and nglob < GLOBAL_MAX:
        j = jobs.pop(0)
        env = dict(os.environ); env.update({k: v for k, v in j[4].items() if k != 'FORCE'})
        if j[2]:
            env['OFFSETS'] = ' '.join(j[2])
        env['START'] = str(j[3])
        dom = free.pop(0)
        out = open(S + '/logs/run_%s_%s_%d.log' % (j[0], j[1], j[3]), 'a')
        p = subprocess.Popen([RUNNER, j[0], j[1], str(dom)], stdout=out, stderr=subprocess.STDOUT, env=env)
        running[p] = (dom, j)
        last_start = time.time(); nglob += 1
        log.write('%s start %s %s offs=%s start=%d dom=%d\n' % (time.strftime('%T'), j[0], j[1], ','.join(j[2] or ['default']), j[3], dom)); log.flush()
    time.sleep(3)
log.write('%s queue %s finished\n' % (time.strftime('%F %T'), sys.argv[1])); log.flush()
