#!/usr/bin/env bash
# cpp_run_timing.sh [methods...]: node timing on a QUIET machine (edge_run_timing.sh style): ONE container at a time, rate 1.0,
# hall_t1_L3 + aisles_t1_L3, offsets 0.0 0.6, OVTIME=1 -> results/cpp_port/<TD>/<seq>/<method>/run_XX.
# CPUS=<list> -> docker --cpuset-cpus. Logs load + GPU utilisation per run into tables/<TD>_load.txt.
set -euo pipefail
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad
TD=${TD:-timing}
G=/home/sasa/workspace/savior_ws/results/cpp_port/tables/${TD}_load.txt
{ date; uptime; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader; docker ps --format '{{.Names}}' | tr '\n' ' '; echo; } >> $G
for seq in hall_t1_L3 aisles_t1_L3; do
  for m in "$@"; do
    echo "$(date +%T) START $seq $m load=$(cut -d' ' -f1 /proc/loadavg) gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader) others=$(docker ps --format '{{.Names}}' | grep -vc '^cppport_' || true)" >> $G
    OVTIME=1 DSN=cpp_port/$TD RATE=1.0 OFFSETS="0.0 0.6" $S/cpp/cpp_run.sh $seq $m 31 > $S/cpp/logs/${TD}_${seq}_$m.log 2>&1
    echo "$(date +%T) END   $seq $m load=$(cut -d' ' -f1 /proc/loadavg) gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader)" >> $G
  done
done
