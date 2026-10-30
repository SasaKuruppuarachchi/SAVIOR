#!/usr/bin/env python3
"""queue.py <jobs file> <max parallel>: run 'ds seq method' lines with run_method.sh, domains 120..219 recycled.
Lines starting with # are skipped; a job is skipped if its results dir already has all runs (runs_summary + n runs)."""
import os, subprocess, sys, time
SCR = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH'
jobs = [l.split() for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
par = int(sys.argv[2])
free = list(range(120, 220))
running = {}
log = open(SCR + '/logs/queue.log', 'a')
def done(p, dom, j):
    log.write('%s done %s rc=%s\n' % (time.strftime('%T'), ' '.join(j), p.returncode)); log.flush(); free.append(dom)
while jobs or running:
    for p in list(running):
        if p.poll() is not None:
            done(p, *running.pop(p))
    while jobs and len(running) < par:
        j = jobs.pop(0)
        env = dict(os.environ)
        if len(j) > 3: env['OFFSETS'] = j[3].replace(',', ' ')
        if len(j) > 4: env['START'] = j[4]
        dom = free.pop(0)
        out = open(SCR + '/logs/run_%s_%s_%s.log' % (j[0], j[1], j[2].replace('+', '_')), 'a')
        p = subprocess.Popen([SCR + '/run_method.sh', j[0], j[1], j[2], str(dom)], stdout=out, stderr=subprocess.STDOUT, env=env)
        running[p] = (dom, j)
        log.write('%s start %s dom=%d\n' % (time.strftime('%T'), ' '.join(j), dom)); log.flush()
    time.sleep(5)
