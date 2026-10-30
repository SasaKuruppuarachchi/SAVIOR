#!/usr/bin/env bash
# status.sh: per method, number of sequences complete (run_10 trajectory present, no container running)
R=/home/sasa/workspace/savior_ws/results/edge_study/runs
RUN=$(docker ps --format '{{.Names}}' | grep '^edge_e_')
for m in $(ls $R/*/ | grep '^e_' | sort -u); do
  n=0; for d in $R/*_t1_*/$m; do s=$(basename $(dirname $d)); [[ -s $d/run_10/stamped_traj_estimate.txt ]] && ! echo "$RUN" | grep -q "edge_${m}_${s}_" && n=$((n+1)); done
  r=$(echo "$RUN" | grep -c "edge_${m}_\(hall\|aisles\)")
  echo "$m $n/8 running=$r"
done
