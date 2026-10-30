#!/usr/bin/env bash
# queue.sh <jobs file> <parallel> : each line "<seq> <tag> [KEY=VAL ...]" (RUNS=1,5 allowed) -> vrun.sh; logs in scratch
set -uo pipefail
J=$1; P=$2
V=/home/sasa/workspace/savior_ws/results/vins_savior
export L=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/vs/logs
grep -v '^#' $J | grep . | xargs -P $P -L 1 bash -c "$V"'/scripts/vrun.sh "$0" "$@" > $L/run_$0_$1.log 2>&1; echo "done $0 $1"' 
