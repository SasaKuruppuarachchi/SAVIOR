"""timing.py <threads> <out.jsonl> [perception_offline args...]: offline pipeline with cv2/numpy thread limits."""
import os, sys
th = int(sys.argv[1])
if th > 0:
    for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ[k] = str(th)
import cv2
if th > 0:
    cv2.setNumThreads(th)
sys.path.insert(0, '/home/sasa/workspace/savior_ws/src/savior/savior_bringup/tools')
import perception_offline as po
sys.exit(po.main(['--stats', sys.argv[2]] + sys.argv[3:]))
