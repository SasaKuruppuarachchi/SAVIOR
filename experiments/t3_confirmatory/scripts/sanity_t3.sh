#!/usr/bin/env bash
# sanity_t3.sh [traj_id ...] : t3 SANITY (as for t2): ONLY openvins + oracle_moving_ext (back-end v2, frozen settings),
# offsets 0.0 / 0.3 / 0.6 s, on L0 and L3 of each trajectory; no SAVIOR / YOLO method. Purpose: catch broken sequences
# (e.g. trajectories that fail to initialise). Then savior-eval (posyaw) and the mechanical exclusion rule (t3_checks.py).
# -> results/t3_confirmatory/sanity/<seq>/<method>/run_0{1,2,3}, EXCLUSIONS.yaml, tables/checks.md
set -euo pipefail
WS=/home/sasa/workspace/savior_ws; T=$WS/results/t3_confirmatory; D=$T/scripts; BV2=$WS/results/backend_v2/scripts
PAR=${PAR:-4}
IDS=${*:-$(docker run --rm -i --network none -v $WS:$WS savior:humble-cuda12.8 python3 -c "
import yaml; print(' '.join(t['id'] for t in yaml.safe_load(open('$T/DESIGN.yaml'))['dataset']['trajectories']))")}
J=$(mktemp); i=0
for id in $IDS; do for k in 0 3; do for m in openvins oracle_moving_ext; do
  f=$T/sanity/${id}_t3_L$k/$m/run_03/stamped_traj_estimate.txt
  [[ -s $f ]] || { echo "${id}_t3_L$k $m $((140 + i % 60))"; i=$((i+1)); }
done; done; done > $J
echo "sanity jobs: $(wc -l < $J)"
xargs -P $PAR -L 1 bash -c 'SANITY=1 '$D'/run_t3_ov2.sh $0 $1 $2 > /dev/null 2>&1 || echo "sanity run failed $0 $1"' < $J
rm -f $J
$BV2/bpy.sh env ROOT=$T/sanity $BV2/eval_bv2.sh > /dev/null
docker run --rm -i --network none -v $WS:$WS savior:humble-cuda12.8 python3 -I $D/t3_checks.py
