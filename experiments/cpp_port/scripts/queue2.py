#!/usr/bin/env python3
"""queue.py <jobs file> <max parallel>: run 'seq method' lines through cpp_run.sh, at most N containers at once."""
import subprocess, sys, time
SCR = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad'
jobs = [l.split() for l in open(sys.argv[1]) if l.strip() and not l.startswith('#')]
N = int(sys.argv[2])
dom0 = int(sys.argv[3]) if len(sys.argv) > 3 else 160
running = []
k = 0
t0 = time.time()
while jobs or running:
    running = [(p, j) for p, j in running if p.poll() is None]
    n_cont = int(subprocess.run("docker ps --filter name=cppport_ -q | wc -l", shell=True, capture_output=True, text=True).stdout or 0)
    while jobs and max(len(running), n_cont) < N:
        n_cont += 1
        seq, m = jobs.pop(0)
        log = open(f'{SCR}/cpp/logs/{m}_{seq}.log', 'w')
        p = subprocess.Popen([f'{SCR}/cpp/cpp_run.sh', seq, m, str(dom0 + k % 40)], stdout=log, stderr=subprocess.STDOUT)
        k += 1
        running.append((p, (seq, m)))
        print(f'{time.time() - t0:7.0f}s start {seq} {m}', flush=True)
    time.sleep(10)
print(f'{time.time() - t0:7.0f}s all done', flush=True)
