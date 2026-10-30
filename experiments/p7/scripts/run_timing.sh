#!/usr/bin/env bash
# run_timing.sh : P7 stage F on an IDLE machine. ONE container at a time, rate 1.0, hall_t1_L3 + aisles_t1_L3,
# methods: SAVIOR main (sens_fix1), SAVIOR-adaptive (p7_nb), yolo_naive, each with segmenter.fast_masks on/off,
# plus OpenVINS alone (baseline launch, no perception node); 3 offsets each; OVTIME=1 -> ov_msckf timing file per run.
# -> results/p7/timing/<seq>/<method>/run_XX ; then p7timing.py -> tables/timing.{json,md}
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentN
n=$(docker ps --format '{{.Names}}' | grep -c '^agentN' || true)
[[ $n -eq 0 ]] || { echo "refusing: $n agentN containers running (timing needs an idle machine)"; exit 4; }
G=$D/../tables/timing_load.txt
{ date; uptime; nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader; } | tee $G
python3 $D/mkmethods.py > /dev/null
for seq in hall_t1_L3 aisles_t1_L3; do
  for m in openvins tim_sens_fix1_fast tim_p7_nb_fast tim_yolo_naive_fast tim_sens_fix1_slow tim_p7_nb_slow tim_yolo_naive_slow; do
    OVTIME=1 DSN=p7/timing RATE=1.0 OFFSETS="0.0 0.6 1.2" $D/run_method.sh $seq $m 231 > $S/logs/timing_${seq}_$m.log 2>&1
    echo "$(date +%T) $seq $m load=$(cut -d' ' -f1 /proc/loadavg) gpu=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader)" | tee -a $G
  done
done
python3 $D/p7timing.py
