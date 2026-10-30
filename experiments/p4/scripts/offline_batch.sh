#!/usr/bin/env bash
for s in cafe1-1 cafe1-2 office1-7 office1-5; do
  DOM=223 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline.sh $s off_$s > /dev/null 2>&1
  DOM=223 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline.sh $s mot_$s --set motion.enable=true > /dev/null 2>&1
  DOM=223 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline.sh $s motgate_$s --set motion.enable=true --set gating.link_depth=contact --set gating.max_noise_m=0.5 > /dev/null 2>&1
  DOM=223 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline.sh $s gate_$s --set gating.link_depth=contact --set gating.max_noise_m=0.5 > /dev/null 2>&1
done
for s in office_s1_06h office_s1_12h; do
  DOM=223 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline_u.sh $s off_$s --start 20 --duration 200 > /dev/null 2>&1
  DOM=223 /tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/agentH/offline_u.sh $s mot_$s --start 20 --duration 200 --set motion.enable=true > /dev/null 2>&1
done
echo done
