#!/usr/bin/env bash
# rw_eval.sh [method dir ...] : savior-eval multi (posyaw, full sequence; the protocol) for results/real_world/runs/<seq>/<method>,
# run in the savior image. Default: every method dir. GT = data/monado/gt/<seq>.txt.
WS=/home/sasa/workspace/savior_ws; R=$WS/results/real_world/runs
DIRS=${@:-$(ls -d $R/*/*/)}
CMD=""
for d in $DIRS; do
  d=${d%/}; m=$(basename $d); seq=$(basename $(dirname $d)); gt=$WS/data/monado/gt/$seq.txt
  ls $d/run_*/stamped_traj_estimate.txt >/dev/null 2>&1 || continue
  CMD="$CMD savior-eval multi --runs $d --gt $gt --label $m --no-plot > $d/eval_multi.log 2>&1 || echo 'eval fail $d';"
done
docker run --rm -i --name rw_eval_$$ --network none --ipc private -u $(id -u):$(id -g) -v $WS:$WS -e HOME=/tmp -e MPLCONFIGDIR=/tmp -w /tmp \
  savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; $CMD"
