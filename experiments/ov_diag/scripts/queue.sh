#!/usr/bin/env bash
# queue.sh <jobs.txt> : launch "seq variant" jobs (run_ov.sh) keeping <= MAXC (12) of OUR containers (ovdiag_* / sota_*) alive.
# Skips jobs whose 10 run dirs already have run_info.yaml with status ok.
set -uo pipefail
WS=/home/sasa/workspace/savior_ws
MAXC=${MAXC:-12}
mine() { docker ps --format '{{.Names}}' | grep -cE '^(ovdiag_|sota_)'; }
while read -r SEQ VAR; do
  [[ -z "$SEQ" || $SEQ == \#* ]] && continue
  n=$(ls $WS/results/ov_diag/runs/$SEQ/$VAR/run_*/run_info.yaml 2>/dev/null | wc -l)
  [[ $n -ge 10 ]] && { echo "skip $SEQ $VAR"; continue; }
  docker ps --format '{{.Names}}' | grep -q "^ovdiag_${VAR}_${SEQ}$" && { echo "running $SEQ $VAR"; continue; }
  while [[ $(mine) -ge $MAXC ]]; do sleep 20; done
  echo "$(date +%T) launch $SEQ $VAR"
  nohup $WS/results/ov_diag/scripts/run_ov.sh $SEQ $VAR < /dev/null > $WS/results/ov_diag/logs/${VAR}_$SEQ.log 2>&1 &
  sleep 5
done < "$1"
wait
echo "$(date +%T) queue done"
