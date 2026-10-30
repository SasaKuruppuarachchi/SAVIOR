#!/usr/bin/env bash
# job.sh <dom> <ds> <seq> <method> [extra...]
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentF
dom=$1; ds=$2; seq=$3; m=$4; shift 4
# CycloneDDS: domain id must be <= 232 (port mapping); containers are network-isolated, so reuse is harmless
dom=$(( (dom % 100) + 120 ))
echo "$(date +%T) start $ds $seq $m dom=$dom" >> $S/logs/queue.log
if [[ $ds == uhumans2 && $m != openvins ]]; then export PSET_EXTRA="tracker.enable=false"; set -- -- backend:=yolo; fi
$S/run_method.sh $ds $seq $m $dom 1 "$@" > $S/logs/final_${seq}_${m}.log 2>&1
echo "$(date +%T) done $ds $seq $m rc=$?" >> $S/logs/queue.log
