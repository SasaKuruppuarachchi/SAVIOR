#!/usr/bin/env bash
# run_method_dm.sh <seq> <method> <ros1.bag> : = run_method.sh (frozen, unchanged) but runs run_one_dm.sh through
# drun_sota_dm.sh (DynaVINS + SAVIOR masks, P10; image savior-sota:noetic-mask-dyna by default)
# one container, runs in series -> $ROOT/<dataset>_<seq>/<method>/run_XX
# env: RUNS (run indices, default "1 2 ... 10"), OFFSETS_FILE (default <DATASET>_offsets.txt: run_XX <- XX-th offset),
#      FROMSTART=1 (single run, offset 0 = bag start, method dir <method>_fromstart, run_01),
#      ROOT (default $WS/results/sota), DATASET (viode | warehouse), RATE (0.5), SOTA_CPUS (4), MDIR_NAME (method dir),
#      SOTA_IMAGE, SOTA_MASK_* / SOTA_DETERMINISTIC (P9, see run_one.sh)
set -euo pipefail
SEQ=$1; METHOD=$2; BAG=$3
WS=${SAVIOR_WS:-/home/sasa/workspace/savior_ws}
D=$(cd "$(dirname "$0")" && pwd)
ROOT=${ROOT:-$WS/results/sota}; DATASET=${DATASET:-viode}; RATE=${RATE:-0.5}
OFFS=($(awk -v s=$SEQ '$1==s{gsub(",", " ", $2); print $2}' ${OFFSETS_FILE:-$D/${DATASET}_offsets.txt}))
RUNS=${RUNS:-1 2 3 4 5 6 7 8 9 10}
MDIR=${MDIR_NAME:-$METHOD}; PAIRS=""   # MDIR_NAME: output method dir (e.g. one per mask set)
if [[ -n "${FROMSTART:-}" ]]; then MDIR=${METHOD}_fromstart; PAIRS="1:0.0"
else [[ ${#OFFS[@]} -gt 0 ]] || { echo "no offsets for $SEQ"; exit 2; }
     for i in $RUNS; do PAIRS="$PAIRS $i:${OFFS[$((i-1))]}"; done; fi
OUT=$ROOT/${DATASET}_$SEQ/$MDIR
[[ $ROOT == $WS/* ]] || export SOTA_ROOT=$ROOT
mkdir -p "$OUT"
INNER="for p in $PAIRS; do i=\${p%%:*}; off=\${p#*:}; R=$OUT/run_\$(printf %02d \$i); rm -rf \$R; mkdir -p \$R; \
  bash $D/run_one_dm.sh $METHOD $BAG \$R \$off $RATE > \$R/run.log 2>&1 || echo \"run \$i rc=\$?\"; \
  grep -E '^(status|n_poses|wall_time_s):' \$R/run_info.yaml | tr '\n' ' '; echo \" [$SEQ $MDIR run_\$i off \$off]\"; done"
NAME="dm_$(echo ${MDIR}_${SEQ} | tr '+' '_')_$$"
SOTA_SEQ=$SEQ SOTA_DATASET=$DATASET SOTA_IMAGE=${SOTA_IMAGE:-savior-sota:noetic-mask-dyna} exec $D/drun_sota_dm.sh "$NAME" "$(dirname "$BAG")" bash -c "$INNER"
