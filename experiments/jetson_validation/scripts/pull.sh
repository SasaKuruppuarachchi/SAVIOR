#!/usr/bin/env bash
# pull the Jetson package out/ (results only; no home/ caches, no roslog) into results/jetson_validation/raw/device_out
mkdir -p /home/sasa/workspace/savior_ws/results/jetson_validation/raw/device_out
rsync -a --exclude home/ --exclude roslog/ --exclude '*.tmp.npz' jetson8gb:savior_jetson/savior_jetson_pkg_v1/out/ /home/sasa/workspace/savior_ws/results/jetson_validation/raw/device_out/
