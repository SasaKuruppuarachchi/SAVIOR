#!/usr/bin/env bash
# cr_eval.sh [method dir ...] : savior-eval multi (posyaw, full sequence; = real_world rw_eval.sh settings) for chi2-realworld method dirs,
# in ONE savior-image container (frozen workspace install/ savior-eval). Default: every method dir. GT = data/monado/gt/<seq>.txt.
WS=/home/sasa/workspace/savior_ws; R=$WS/results/chi2_realworld/runs
DIRS=${@:-$(ls -d $R/*/*/)}
CMD=""
for d in $DIRS; do
  d=${d%/}; m=$(basename $d); seq=$(basename $(dirname $d)); gt=$WS/data/monado/gt/$seq.txt
  ls $d/run_*/stamped_traj_estimate.txt >/dev/null 2>&1 || continue
  CMD="$CMD savior-eval multi --runs $d --gt $gt --label $m --no-plot > $d/eval_multi.log 2>&1 || echo 'eval fail $d';"
done
docker run --rm -i --name c2eval_$$ --network none --ipc private -u $(id -u):$(id -g) -v $WS:$WS -e HOME=/tmp -e MPLCONFIGDIR=/tmp -w /tmp \
  savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; $CMD"
