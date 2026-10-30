#!/usr/bin/env bash
# build_v2.sh <tag>: python-only overlay $SCR/install_<tag> (savior_perception + savior_bringup) on top of $SCR/install
T=$1
exec /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/drun.sh 231 agentH_build_$T "cd /home/sasa/workspace/savior_ws && colcon --log-base /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/log_$T build --base-paths src/savior --packages-select savior_perception savior_bringup --build-base /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/build_$T --install-base /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/install_$T 2>&1 | tail -3"
