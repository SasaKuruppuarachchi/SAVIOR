#!/usr/bin/env bash
# nv_eval.sh [method dir ...] : savior-eval multi (posyaw, full sequence; = eval_bv2.sh / eval_e.sh / rw_eval.sh) for NIS-validation
# method dirs, in ONE savior-image container (frozen workspace install/ savior-eval, as for the baselines). Default: every method dir.
WS=/home/sasa/workspace/savior_ws; R=$WS/results/nis_validation/runs
DIRS=${@:-$(ls -d $R/*/*/*/)}
CMD=""
for d in $DIRS; do
  d=${d%/}; m=$(basename $d); seq=$(basename $(dirname $d)); set=$(basename $(dirname $(dirname $d)))
  case $set in
    t2|ctl) gt=$WS/data/warehouse/gt/$seq.txt ;;
    viode) gt=$WS/data/viode/gt/$seq.txt ;;
    e) gt=$WS/data/${seq%%_*}/gt/${seq#*_}.txt ;;
    rw) gt=$WS/data/monado/gt/$seq.txt ;;
  esac
  [[ -f $gt ]] || { echo "no gt $d"; continue; }
  ls $d/run_*/stamped_traj_estimate.txt >/dev/null 2>&1 || continue
  CMD="$CMD savior-eval multi --runs $d --gt $gt --label $m --no-plot > $d/eval_multi.log 2>&1 || echo 'eval fail $d';"
done
S=/tmp/claude-1002/-home-sasa-workspace-savior-ws/c06f990f-0719-4913-a626-9c3ce83cc885/scratchpad/nv
mkdir -p $S/home
docker run --rm -i --name nv_eval_$$ --network none --ipc private -v $WS:$WS -v /tmp/claude-1002:/tmp/claude-1002 -e HOME=$S/home -e MPLCONFIGDIR=$S/home/mpl -w /tmp \
  savior:humble-cuda12.8 bash -c "source /opt/ros/humble/setup.bash; source $WS/install/setup.bash; $CMD"
