#!/usr/bin/env python3
"""Stand-in for `ros2 launch ...` used by test_runner.py.

modes: ok      write a trajectory, exit 0 (launch shut down itself)
       hang    write a trajectory, then never exit (needs SIGINT)
       pattern print a 'bag finished' line, write on SIGINT, then exit
       nooutput exit 1 without writing
"""
import argparse
import signal
import sys
import time


def write(path, n=50):
    with open(path, 'w') as f:
        f.write('# timestamp(s) tx ty tz qx qy qz qw\n')
        for i in range(n):
            f.write('%.5f %.6f 0 0 0 0 0 1\n' % (i * 0.1, i * 0.1))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', default='ok')
    p.add_argument('args', nargs='*')   # config:=... bag:=... output:=...
    a = p.parse_args()
    kv = dict(s.split(':=', 1) for s in a.args if ':=' in s)
    out = kv.get('output')
    print('fake launch', kv, flush=True)

    def on_sigint(*_):
        if a.mode == 'pattern':
            write(out)
        print('got SIGINT, exiting', flush=True)
        sys.exit(0)
    signal.signal(signal.SIGINT, on_sigint)

    if a.mode == 'ok':
        write(out)
        return 0
    if a.mode == 'nooutput':
        return 1
    if a.mode == 'hang':
        write(out)
    if a.mode == 'pattern':
        time.sleep(0.5)
        print('[INFO] [ros2-3]: process has finished cleanly [pid 42]',
              flush=True)
    while True:
        time.sleep(0.1)


if __name__ == '__main__':
    sys.exit(main())
