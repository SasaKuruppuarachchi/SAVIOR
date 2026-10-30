#!/usr/bin/env bash
# offline_all.sh seq... : offline_eval.py (YOLO + P4 variants vs GT) for each sequence, in one GPU container
S=/home/sasa/workspace/savior_ws/results/p5_viode
exec $S/scripts/drun.sh ${DOM:-226} agentI_offline_$$ bash -c "source /opt/ros/humble/setup.bash; source install/setup.bash; cd /tmp; for q in $*; do python3 $S/scripts/offline_eval.py --seq \$q --out $S/offline/\$q.yaml --inst-out $S/offline/\${q}_inst.jsonl > $S/offline/\$q.log 2>&1 || echo fail \$q; done"
