#!/usr/bin/env bash
# rw_dispatch.sh <seq> <method> <domain> : bv2queue.py RUNNER for the real-world study (OpenVINS family -> run_rw.sh,
# vins_fusion / dynavins / ros1conv -> rw_sota.sh)
D=$(cd "$(dirname "$0")" && pwd)
case $2 in vins_fusion|dynavins|ros1conv) exec $D/rw_sota.sh "$@" ;; *) exec $D/run_rw.sh "$@" ;; esac
