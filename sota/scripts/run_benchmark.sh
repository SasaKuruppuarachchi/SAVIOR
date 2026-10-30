#!/usr/bin/env bash
# run_benchmark.sh <jobs file> : lines "<seq> <method> [<method>...]" ('#' = comment); sequences run one after another
# (PARSEQ sequences in parallel, default 2 -> 2 x #methods containers), each through run_sequence.sh (temporary bag
# deleted after the sequence). Pauses (exits) if free disk < MIN_FREE_GB (default 30).
set -uo pipefail
D=$(cd "$(dirname "$0")" && pwd)
PARSEQ=${PARSEQ:-2}; MIN_FREE_GB=${MIN_FREE_GB:-30}
WS=${SAVIOR_WS:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}   # colcon workspace (<ws>/src/savior/sota/scripts/..)
while read -r seq methods; do
  while (( $(jobs -rp | wc -l) >= PARSEQ )); do sleep 5; done
  free=$(df --output=avail -BG "$WS" | tail -1 | tr -dc 0-9)
  (( free >= MIN_FREE_GB )) || { echo "free disk ${free} GB < ${MIN_FREE_GB} GB: stopping"; wait; exit 3; }
  echo "$(date +%T) start $seq: $methods"
  $D/run_sequence.sh $seq $methods < /dev/null > "${LOGDIR:-/tmp}/sota_$seq.log" 2>&1 &
done < <(grep -v '^\s*#' "$1" | grep -v '^\s*$')
wait
