#!/usr/bin/env bash
# status.sh [step] - read-only progress overview: state + exit code of every started step, the last lines of the
# running/selected step's console log, our running containers (saviorsj_*), memory, temperature, disk.
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; O="$(dirname "${D}")/out"
printf '%-18s %-10s %s\n' STEP STATE "EXIT / STARTED"
for p in "${O}"/status/*.pid; do
    [[ -f "${p}" ]] || continue
    s="$(basename "${p}" .pid)"
    if [[ -f "${O}/status/${s}.exit" ]]; then st="done"; ex="exit=$(cat "${O}/status/${s}.exit")"
    elif kill -0 "$(cat "${p}")" 2>/dev/null; then st="RUNNING"; ex="since $(date -r "${p}" '+%F %T')"
    else st="died?"; ex="no exit file (killed / reboot?)"; fi
    printf '%-18s %-10s %s\n' "${s}" "${st}" "${ex}"
    [[ "${st}" == RUNNING || "${s}" == "${1:-}" ]] && { echo "  --- tail ${s}.console.log"; tail -n "${N:-8}" "${O}/logs/${s}.console.log" | sed 's/^/  /'; }
done
echo "--- steps.log (last 5)"; tail -n 5 "${O}/logs/steps.log" 2>/dev/null | sed 's/^/  /'
echo "--- our containers: $(docker ps --format '{{.Names}} ({{.Status}})' 2>/dev/null | grep '^saviorsj_' | tr '\n' ' ')"
echo "--- MemAvailable $(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo) MB, load $(cut -d' ' -f1-3 /proc/loadavg), max temp $(cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | sort -n | tail -1 | awk '{print $1/1000}') C, disk free $(df -Ph "${O}" | awk 'NR==2{print $4}')"
