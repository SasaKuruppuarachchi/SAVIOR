#!/usr/bin/env bash
# queue.sh <jobs file> <parallel>   : run "seq method idx dom" lines, N at a time
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentG
D=$(dirname $(readlink -f $0))
export S D
cat $1 | xargs -P $2 -L 1 bash -c 'echo "$(date +%T) start $0 $1 $2 dom=$3" >> $S/logs/queue.log; '"$D"'/run1.sh $0 $1 $2 $3 > $S/logs/${0}_${1}_${2}.log 2>&1; echo "$(date +%T) done $0 $1 $2 rc=$?" >> $S/logs/queue.log'
