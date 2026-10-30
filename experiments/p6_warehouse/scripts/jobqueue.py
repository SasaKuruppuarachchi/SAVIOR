#!/usr/bin/env python3
"""queue.py <jobs file> <max parallel> [max yolo parallel]: run 'seq method [offsets,comma] [start] [KEY=VAL ...]' lines
with run_method.sh; domains 20..219 recycled. '#' lines skipped. A job is skipped if its method dir already holds
run_XX/stamped_traj_estimate.txt for every requested index. YOLO jobs (method contains 'yolo') are capped separately
(shared GPU)."""
import os, subprocess, sys, time
S = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentL'
R = '/home/sasa/workspace/savior_ws/results/p6_warehouse'
D = os.path.dirname(os.path.abspath(__file__))
OFFS = '0.0 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 1.8'.split()
jobs = []
for l in open(sys.argv[1]):
    if not l.strip() or l.startswith('#'):
        continue
    p = l.split()
    seq, m = p[0], p[1]
    offs = p[2].split(',') if len(p) > 2 and p[2] != '-' else OFFS
    start = int(p[3]) if len(p) > 3 and p[3] != '-' else 1
    env = dict(x.split('=', 1) for x in p[4:])
    idx = range(start, start + len(offs))
    have = all(os.path.isfile(f'{R}/{seq}/{m}/run_{i:02d}/stamped_traj_estimate.txt') and
               os.path.getsize(f'{R}/{seq}/{m}/run_{i:02d}/stamped_traj_estimate.txt') > 0 for i in idx)
    if have:
        continue
    jobs.append((seq, m, offs, start, env))
par = int(sys.argv[2]); ypar = int(sys.argv[3]) if len(sys.argv) > 3 else par
free = list(range(int(os.environ.get('DOM_LO', '20')), int(os.environ.get('DOM_HI', '220'))))   # isolated containers; distinct ranges per queue anyway
STAGGER = float(os.environ.get('STAGGER_S', '20'))   # P6: stagger container starts (P5: mask drops when ~25 start at once)
last_start = 0.0
GLOBAL_MAX = int(os.environ.get('GLOBAL_MAX', '1000'))   # cap on ALL agentL_ containers (other queues included)
running = {}
os.makedirs(S + '/logs', exist_ok=True)
log = open(S + '/logs/queue.log', 'a')
log.write('%s queue %s: %d jobs\n' % (time.strftime('%T'), sys.argv[1], len(jobs))); log.flush()
while jobs or running:
    for p in list(running):
        if p.poll() is not None:
            dom, j = running.pop(p)
            log.write('%s done %s %s rc=%s\n' % (time.strftime('%T'), j[0], j[1], p.returncode)); log.flush()
            free.append(dom)
    ny = sum(1 for _, j in running.values() if 'yolo' in j[1])
    k = 0
    nglob = int(subprocess.run("docker ps --format '{{.Names}}' | grep -c '^agentL_'", shell=True, capture_output=True, text=True).stdout.strip() or 0)
    while k < len(jobs) and len(running) < par and time.time() - last_start >= STAGGER and nglob < GLOBAL_MAX:
        j = jobs[k]
        if 'yolo' in j[1] and ny >= ypar:
            k += 1
            continue
        jobs.pop(k)
        env = dict(os.environ); env.update(j[4])
        env['OFFSETS'] = ' '.join(j[2]); env['START'] = str(j[3])
        dom = free.pop(0)
        out = open(S + '/logs/run_%s_%s_%d.log' % (j[0], j[1].replace('+', '_'), j[3]), 'a')
        p = subprocess.Popen([D + '/run_method.sh', j[0], j[1], str(dom)], stdout=out, stderr=subprocess.STDOUT, env=env)
        running[p] = (dom, j)
        last_start = time.time()
        nglob += 1
        ny += 'yolo' in j[1]
        log.write('%s start %s %s offs=%s start=%d dom=%d\n' % (time.strftime('%T'), j[0], j[1], ','.join(j[2]), j[3], dom)); log.flush()
    time.sleep(3)
log.write('%s queue %s finished\n' % (time.strftime('%T'), sys.argv[1])); log.flush()
