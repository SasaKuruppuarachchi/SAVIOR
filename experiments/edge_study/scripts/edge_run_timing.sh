#!/usr/bin/env bash
# edge_run_timing.sh [methods...]: EDGE timing on a QUIET machine (run_timing.sh style): ONE container at a time, rate 1.0,
# hall_t1_L3 + aisles_t1_L3, offsets 0.0 0.6, OVTIME=1 -> results/edge_study/timing/<seq>/<method>/run_XX.
# CPUS=<list> -> docker --cpuset-cpus (edge CPU budget) and results/edge_study/timing_cpus4. Logs load + GPU util per run.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge
TD=${TD:-timing}
G=/home/sasa/workspace/savior_ws/results/edge_study/tables/${TD}_load.txt
{ date; uptime; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader; docker ps --format '{{.Names}}' | tr '\n' ' '; echo; } >> $G
for seq in hall_t1_L3 aisles_t1_L3; do
  for m in "$@"; do
    echo "$(date +%T) START $seq $m load=$(cut -d' ' -f1 /proc/loadavg) gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader) others=$(docker ps --format '{{.Names}}' | grep -vc '^edge_' || true)" >> $G
    OVTIME=1 DSN=edge_study/$TD RATE=1.0 OFFSETS="0.0 0.6" $D/edge_run.sh $seq $m 231 > $S/logs/${TD}_${seq}_$m.log 2>&1
    echo "$(date +%T) END   $seq $m load=$(cut -d' ' -f1 /proc/loadavg) gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader)" >> $G
  done
done
