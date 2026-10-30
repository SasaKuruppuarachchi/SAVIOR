#!/usr/bin/env bash
# run_pipe_masks.sh (v2) - offline FULL-pipeline masks on the device (lib/pipe_dump.py: Python SaviorPipeline + the device
# engine on every stereo frame) for SAVIOR (main install, s engine) and SAVIOR-edge (frozen_edge install, n engine) on both
# t1 sequences -> out/pipe_masks/device_{main,edge}_<seq>.npz. Compared on the server with the same dump made with the desktop
# engines (verify / jv analysis): per-frame IoU distribution of the final dynamic masks. Resumable (existing npz kept).
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
sj_require_image; sj_require_ws; sj_require_idle_pkg
O="${OUTD}/pipe_masks"; mkdir -p "${O}"
for seq in "${SEQS[@]}"; do
    for v in main edge; do
        f="${O}/device_${v}_${seq}.npz"
        [[ -f "${f}" ]] && { log "pipe_masks: ${f} exists"; continue; }
        if [[ "${v}" == main ]]; then src="source ${INSTALL_MAIN}/setup.bash"; eng="${MODEL_S}"; x=""
        else src="source ${INSTALL_MAIN}/setup.bash; source ${INSTALL_EDGE}/setup.bash"; eng="${MODEL_N}"; x="--edge"; fi
        log "pipe_masks: ${v} ${seq}"
        sj_docker "pipe_${v}_${seq}" "${src}; python3 ${LIB}/pipe_dump.py --seq ${seq} --engine ${eng} --out ${f}.tmp.npz ${x} && mv ${f}.tmp.npz ${f}" \
            > "${O}/dump_${v}_${seq}.log" 2>&1 || die "pipe_dump ${v} ${seq} failed (${O}/dump_${v}_${seq}.log)"
        tail -1 "${O}/dump_${v}_${seq}.log"
    done
done
log "pipe_masks: done"
