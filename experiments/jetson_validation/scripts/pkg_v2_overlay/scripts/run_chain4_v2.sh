#!/usr/bin/env bash
# run_chain4_v2.sh [pid] - (written 2026-10-25 00:25, after the first C++ accuracy preview showed a 1.9 m outlier of SAVIOR (C++)
# on hall_t1_L3 at offset 1.2 s): the remaining 7 desktop offsets (0.2 0.4 0.8 1.0 1.4 1.6 1.8 s = run_02/03/05/06/08/09/10) of
# hall_t1_L3 for SAVIOR (C++) and SAVIOR-edge (C++), back-end v1, rate 0.5, frozen settings -> out/accuracy_hall10, so the device
# has the same 10-offset sample as the desktop reference on the hardest t1 sequence. Evaluated on the server.
set -uo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${D}/common.sh"
step() { echo "[chain4] $(date '+%F %T') $*"; }
if [[ -n "${1:-}" ]]; then step "waiting for pid $1"; while kill -0 "$1" 2>/dev/null; do sleep 20; done; fi
P="2:0.2,3:0.4,5:0.8,6:1.0,8:1.4,9:1.6,10:1.8"
dom=170
for m in savior_cpp savior_edge_cpp; do
    dom=$((dom + 1))
    [[ -f "${OUTD}/accuracy_hall10/hall_t1_L3/${m}/run_10/run_info.yaml" ]] && continue
    step "hall10 ${m}"
    SJ_DOMAIN=${dom} sj_docker "acc10_${m}" "bash ${LIB}/run_one.sh hall_t1_L3 ${m} accuracy_hall10 0.5 ${P}" > "${OUTD}/logs/acc10_${m}.log" 2>&1 || true
done
step "chain4 done"
