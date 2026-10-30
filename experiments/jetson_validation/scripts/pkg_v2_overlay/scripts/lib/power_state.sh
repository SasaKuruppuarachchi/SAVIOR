#!/usr/bin/env bash
# power_state.sh <out.json> : READ-ONLY snapshot of the Jetson power / clock / thermal state (host side, no sudo).
# nvpmodel -q, CPU cpufreq cur/min/max per core, GPU devfreq cur/min/max, inferred jetson_clocks state, thermal zones,
# load average. Never changes anything (no nvpmodel -m, no jetson_clocks).
set -uo pipefail
OUT="$1"
pm="$(timeout 10 nvpmodel -q 2>/dev/null | sed -n 's/^NV Power Mode: *//p' | head -1)"
pmid="$(timeout 10 nvpmodel -q 2>/dev/null | tail -1 | tr -dc '0-9')"
cpu=""; lock=1
for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
    [[ -r "${c}/scaling_cur_freq" ]] || continue
    n="$(basename "$(dirname "${c}")")"; cur=$(cat "${c}/scaling_cur_freq"); mn=$(cat "${c}/scaling_min_freq"); mx=$(cat "${c}/scaling_max_freq")
    cpu+="\"${n}\": [${cur}, ${mn}, ${mx}], "; [[ "${mn}" == "${mx}" ]] || lock=0
done
g="$(ls -d /sys/class/devfreq/*gpu* /sys/class/devfreq/17000000.* 2>/dev/null | head -1)"
gcur=$(cat "${g}/cur_freq" 2>/dev/null || echo 0); gmin=$(cat "${g}/min_freq" 2>/dev/null || echo 0); gmax=$(cat "${g}/max_freq" 2>/dev/null || echo 0)
[[ "${gmin}" == "${gmax}" && "${gmax}" != 0 ]] || lock=0
th=""; for z in /sys/class/thermal/thermal_zone*; do th+="\"$(cat "${z}/type" 2>/dev/null)\": $(( $(cat "${z}/temp" 2>/dev/null || echo 0) / 1000 )), "; done
cat > "${OUT}" <<J
{"date": "$(date -Is)", "epoch": $(date +%s.%N), "power_mode": "${pm:-unknown}", "power_mode_id": "${pmid}",
 "jetson_clocks_inferred": "$([[ ${lock} == 1 ]] && echo on || echo off)",
 "cpu_khz_cur_min_max": {${cpu%, }}, "gpu_hz_cur_min_max": [${gcur}, ${gmin}, ${gmax}], "gpu_devfreq": "${g}",
 "thermal": {${th%, }}, "loadavg": "$(cut -d' ' -f1-3 /proc/loadavg)",
 "mem_available_mb": $(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo),
 "other_containers": "$(docker ps --format '{{.Names}}' 2>/dev/null | grep -v '^saviorsj_' | tr '\n' ' ')"}
J
echo "power: mode='${pm:-unknown}' jetson_clocks=$([[ ${lock} == 1 ]] && echo on || echo off) gpu ${gcur}/${gmax} Hz load $(cut -d' ' -f1 /proc/loadavg)"
