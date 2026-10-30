#!/usr/bin/env bash
# waitm.sh <method>: block (<= 580 s) until all 8 sequences of <method> are done in the queue log
Q=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge/logs/queue.log
timeout 580 bash -c "until [ \$(grep -c ' done .* $1 rc' $Q) -ge 8 ]; do sleep 15; done" && echo "$1 COMPLETE" || echo "$1: $(grep -c " done .* $1 rc" $Q)/8"
