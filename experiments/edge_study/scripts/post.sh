#!/usr/bin/env bash
# post.sh <tag> <method ...>: eval (savior-eval multi, in the image) + sync check + paired ATE/RPE vs sens_fix1
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/edge
WS=/home/sasa/workspace/savior_ws
TAG=$1; shift
docker run --rm --network none -v $WS:$WS -v /tmp/claude-1002:/tmp/claude-1002 -e HOME=$S/home -e MPLCONFIGDIR=$S/home/mpl --name edge_post_$TAG savior:humble-cuda12.8 \
  bash -c "source /opt/ros/humble/setup.bash; source $S/ws/install/setup.bash; $S/scripts/edge_eval_all.sh $*; \
           TAG=_$TAG python3 $S/scripts/edge_sync.py $* > /dev/null; \
           python3 $S/scripts/edge_analyze.py --methods $(echo $* | tr ' ' ',') --tag $TAG > /dev/null; \
           METRIC=rpe python3 $S/scripts/edge_analyze.py --methods $(echo $* | tr ' ' ',') --tag $TAG > /dev/null"
