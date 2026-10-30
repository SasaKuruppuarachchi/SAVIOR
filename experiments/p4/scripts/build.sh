#!/usr/bin/env bash
# build.sh [colcon build args...]  -> agentH overlay in $SCR/install (never touches the workspace build/install/log)
SCR=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH
exec $SCR/drun.sh 231 agentH_build_$$ "cd /home/sasa/workspace/savior_ws && colcon --log-base $SCR/log build --base-paths src/savior --build-base $SCR/build --install-base $SCR/install --cmake-args -DCMAKE_BUILD_TYPE=Release $* 2>&1 | tail -25"
