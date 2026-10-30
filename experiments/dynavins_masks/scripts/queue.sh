#!/usr/bin/env bash
# queue.sh <jobs file> <parallel> : each line "<t1|t2|viode> <seq> <tag> [KEY=VAL ...]" -> dmrun.sh; logs in scratch
set -uo pipefail
J=$1; P=$2
R=/home/sasa/workspace/savior_ws/results/dynavins_masks
export L=${DM_SCRATCH:-/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/dm}/logs
mkdir -p $L
grep -v '^#' $J | grep . | xargs -P $P -L 1 bash -c "$R"'/scripts/dmrun.sh "$0" "$@" > $L/run_$1_$2.log 2>&1; echo "done $0 $1 $2"'
