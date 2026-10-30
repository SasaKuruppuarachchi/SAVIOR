#!/usr/bin/env bash
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge
SEQS="hall_t1_L0 hall_t1_L1 hall_t1_L2 hall_t1_L3 aisles_t1_L0 aisles_t1_L1 aisles_t1_L2 aisles_t1_L3"
for k in "$@"; do NAME=edge_detcache_$k $S/epy.sh $S/scripts/detcache_edge.py $k $SEQS; done
