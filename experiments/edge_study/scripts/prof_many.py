import subprocess, sys
S = '/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge'
for v in sys.argv[1].split(','):
    for q in ('hall_t1_L3', 'aisles_t1_L3'):
        subprocess.run(['python3', f'{S}/scripts/edgeprof.py', v, q, '600', f'{S}/prof/{v}_{q}.json'], stdout=subprocess.DEVNULL)
