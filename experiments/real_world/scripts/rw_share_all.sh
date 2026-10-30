#!/usr/bin/env bash
# rw_share_all.sh : rw_share.py for every diag_openvins run -> results/real_world/share/<seq>_run_XX.yaml (savior image)
WS=/home/sasa/workspace/savior_ws; H=$WS/results/real_world; mkdir -p $H/share
CMD=""
for d in $H/runs/*/diag_openvins/run_*; do
  s=$(basename $(dirname $(dirname $d))); r=$(basename $d); f=$(ls $d/diag_updates.csv* 2>/dev/null | head -1)
  [[ -n $f ]] || continue
  CMD="$CMD python3 -I $H/scripts/rw_share.py --diag $f --masks $WS/data/monado/refmasks/$s.npz --klass dyn --out $H/share/${s}_$r.yaml > $H/share/${s}_$r.log 2>&1 || echo 'share fail $d';"
done
docker run --rm -i --name rw_share_$$ --network none -u $(id -u):$(id -g) -v $WS:$WS -e HOME=/tmp -w /tmp savior:humble-cuda12.8 bash -c "$CMD"
