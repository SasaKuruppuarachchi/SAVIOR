#!/usr/bin/env bash
# sync the v2 scripts overlay to the Jetson package and refresh MANIFEST.sha256 for scripts/ + VERSION.txt
J=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/jv
rsync -a $J/pkg/scripts/ jetson8gb:savior_jetson/savior_jetson_pkg_v1/scripts/ && ssh jetson8gb 'cd ~/savior_jetson/savior_jetson_pkg_v1 && chmod +x scripts/*.sh && python3 - <<PY
import hashlib,os
old={}
for ln in open("MANIFEST.sha256"):
    w,rel=ln.rstrip("\n").split("  ",1); old[rel]=w
fs=["VERSION.txt"]+[os.path.join(d,f) for d,_,ff in os.walk("scripts") for f in ff if "__pycache__" not in d]
for rel in fs:
    h=hashlib.sha256(open(rel,"rb").read()).hexdigest()
    if old.get(rel)!=h: print("updated", rel); old[rel]=h
open("MANIFEST.sha256","w").writelines(f"{w}  {r}\n" for r,w in old.items())
PY
python3 scripts/lib/verify_trees.py --quiet'
