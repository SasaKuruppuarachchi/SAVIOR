#!/usr/bin/env bash
# run_one_dm.sh <method> <ros1.bag> <run_dir> <start_offset_s> <rate>   (INSIDE savior-sota:noetic-mask-dyna, --network none)
# = run_one.sh (frozen with results/vins_savior/FREEZE.md5, unchanged) + SAVIOR keys for DynaVINS (patch P10):
#   the SOTA_MASK_* / SOTA_DETERMINISTIC / SOTA_IGNORE_SOLVER_TIME keys are also appended for dynavins, plus
#   SOTA_SOLVER_THREADS -> savior_solver_threads (P10 only). Everything else is identical to run_one.sh.
# method: vins_fusion | dynavins | orbslam3, optional suffix +lc (loop closure on; vins_fusion and orbslam3 only)
# Writes <run_dir>/stamped_traj_estimate.txt (TUM, seconds, IMU/body frame, gravity-aligned world), timing.csv,
# estimator.log, config/ (the exact config used), traj_*.txt (secondary outputs), run_info.yaml.
set -uo pipefail
METHOD=$1; BAG=$2; R=$3; OFF=$4; RATE=$5
SOTA=$(cd "$(dirname "$0")/.." && pwd)
DS=${SOTA_DATASET:-viode}; CD=$SOTA/config/$DS
BASE=${METHOD%%+*}; LC=0; [[ $METHOD == *+lc* ]] && LC=1
mkdir -p "$R/config" "$R/native"
export ROS_MASTER_URI=http://localhost:11311 ROS_HOSTNAME=localhost ROS_LOG_DIR=/tmp/roslog HOME=/tmp
source /opt/sota/catkin_ws/devel/setup.bash
T0=$(date +%s.%N)
status=ok

finish() {  # run_info.yaml (same core keys as savior-run's run_info.yaml in results/p5_viode)
  local n; n=$(grep -vc '^#' "$R/stamped_traj_estimate.txt" 2>/dev/null || echo 0)
  [[ $n -gt 0 ]] || status=no_poses
  python3 - "$R" "$status" "$n" "$T0" "$OFF" "$RATE" "$LC" "$METHOD" "$BAG" "${CFG:-}" <<'PY'
import sys, time, os, yaml
R, status, n, t0, off, rate, lc, method, bag, cfg = sys.argv[1:]
commits = dict(l.strip().split(None, 1) for l in open('/opt/sota/COMMITS.txt') if l.strip())  # P9/P10 lines have 3 fields (run_one.sh bug: no run_info.yaml in the mask images)
info = dict(run=os.path.basename(R), index=int(os.path.basename(R).split('_')[-1]) if R[-2:].isdigit() else None,
            dataset=os.environ.get('SOTA_DATASET', 'viode'), seq=os.environ.get('SOTA_SEQ', ''), method=method,
            status=status, n_poses=int(n), start=time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(float(t0))),
            end=time.strftime('%Y-%m-%dT%H:%M:%S'), wall_time_s=round(time.time() - float(t0), 3),
            start_offset=float(off), rate=float(rate), loop_closure=bool(int(lc)), bag=bag, config=cfg,
            image=os.environ.get('SOTA_IMAGE', 'savior-sota:noetic'), commits=commits,
            traj_frame='T_world_imu (IMU/body frame, gravity-aligned z-up world), TUM, stamps in s')
for k in ('SOTA_MASK_DIR', 'SOTA_MASK_MODE', 'SOTA_MASK_THRESHOLD', 'SOTA_MASK_RELAXED', 'SOTA_MASK_MIN_FEATURES', 'SOTA_MASK_LATENCY_MS', 'SOTA_DETERMINISTIC', 'SOTA_IGNORE_SOLVER_TIME', 'SOTA_SOLVER_THREADS'):
    if os.environ.get(k):
        info.setdefault('savior_keys', {})[k] = os.environ[k].replace('{off}', off)
yaml.safe_dump(info, open(R + '/run_info.yaml', 'w'), sort_keys=False)
PY
}

wait_stable() {  # wait until file $1 stops growing for $2 s (max $3 s)
  local f=$1 quiet=$2 max=$3 last=-1 same=0 t=0 n
  while (( t < max )); do
    n=$(stat -c %s "$f" 2>/dev/null || echo 0)
    if [[ $n == "$last" ]]; then same=$((same + 1)); else same=0; last=$n; fi
    (( same >= quiet )) && return 0
    sleep 1; t=$((t + 1))
  done
}

if [[ $BASE == vins_fusion || $BASE == dynavins ]]; then
  if [[ $BASE == vins_fusion ]]; then
    cp "$CD/vins_fusion/"*.yaml "$R/config/"; CFG=$R/config/calibration.yaml; PKG=vins
  else
    [[ $LC == 1 ]] && { echo "dynavins+lc: not supported (DynaVINS' VIODE setup is BA-only)"; exit 2; }
    cp "$CD/dynavins/"*.yaml "$R/config/"; CFG=$R/config/calibration_stereo.yaml; PKG=dynaVINS
  fi
  # run-time paths only (output_path / pose_graph_save_path); no estimator parameter is changed here
  sed -i -E "s|^output_path:.*|output_path: \"$R/native\"|; s|^pose_graph_save_path:.*|pose_graph_save_path: \"$R/native/pose_graph/\"|" "$CFG"
  # P9 (VINS-Fusion) / P10 (DynaVINS): SAVIOR dynamic masks / deterministic mode, appended as optional keys to the config copy.
  # SOTA_MASK_DIR may contain {off} (replaced by this run's start offset, e.g. masks/<seq>/<method>/off_{off}).
  if [[ ( $BASE == vins_fusion || $BASE == dynavins ) && ( -n "${SOTA_MASK_DIR:-}" || -n "${SOTA_DETERMINISTIC:-}" || -n "${SOTA_SOLVER_THREADS:-}" ) ]]; then
    {
      echo ""; echo "# ---- SAVIOR P9/P10 keys (appended by run_one_dm.sh)"
      if [[ -n "${SOTA_MASK_DIR:-}" ]]; then
        echo "savior_mask_dir: \"${SOTA_MASK_DIR//\{off\}/$OFF}\""
        echo "savior_mask_mode: \"${SOTA_MASK_MODE:-gate}\""
        echo "savior_mask_threshold: ${SOTA_MASK_THRESHOLD:-128}"
        echo "savior_mask_relaxed_threshold: ${SOTA_MASK_RELAXED:-224}"
        echo "savior_mask_min_features: ${SOTA_MASK_MIN_FEATURES:-30}"
        echo "savior_mask_latency_ms: ${SOTA_MASK_LATENCY_MS:-250}"
        echo "savior_mask_wait_ms: ${SOTA_MASK_WAIT_MS:-0}"
        echo "savior_mask_stats: \"$R/mask_stats.csv\""
      fi
      echo "savior_deterministic: ${SOTA_DETERMINISTIC:-0}"
      echo "savior_ignore_solver_time: ${SOTA_IGNORE_SOLVER_TIME:-0}"
      if [[ $BASE == dynavins ]]; then echo "savior_solver_threads: ${SOTA_SOLVER_THREADS:-0}"; fi
    } >> "$CFG"
  elif [[ -n "${SOTA_MASK_DIR:-}" ]]; then
    echo "SOTA_MASK_DIR is only supported for vins_fusion / dynavins"; exit 2
  fi
  roscore -p 11311 > "$R/roscore.log" 2>&1 &
  for i in $(seq 50); do rostopic list > /dev/null 2>&1 && break; sleep 0.2; done
  SOTA_TIMING_FILE=$R/timing.csv rosrun $PKG vins_node "$CFG" > "$R/estimator.log" 2>&1 &
  rosrun sota_tools pose_recorder.py _topic:=/vins_estimator/odometry _out:="$R/traj_vio.txt" > "$R/recorder.log" 2>&1 &
  if [[ $LC == 1 ]]; then
    rosrun loop_fusion loop_fusion_node "$CFG" > "$R/loop_fusion.log" 2>&1 &
    rosrun sota_tools pose_recorder.py _topic:=/loop_fusion/odometry_rect _out:="$R/traj_lc.txt" > "$R/recorder_lc.log" 2>&1 &
  fi
  # wait for the estimator to subscribe to all inputs, then play (rosbag play -s = same semantics as P5 start_offset)
  for i in $(seq 100); do
    n=$(rostopic info /imu0 2>/dev/null | grep -c '\* /vins_estimator'); m=$(rostopic info /cam1/image_raw 2>/dev/null | grep -c '\* /vins_estimator')
    [[ $n -ge 1 && $m -ge 1 ]] && break; sleep 0.2
  done
  sleep 1
  rosbag play -q -r "$RATE" -s "$OFF" -d 1 --queue=1000 "$BAG" > "$R/play.log" 2>&1 || status=play_failed
  wait_stable "$R/traj_vio.txt" 5 120
  [[ $LC == 1 ]] && wait_stable "$R/traj_lc.txt" 5 60
  pgrep -f vins_node > /dev/null || status=estimator_died
  rosnode kill -a > /dev/null 2>&1; sleep 2; pkill -INT -f roscore; pkill -INT -f rosmaster; sleep 1
  pkill -9 -f vins_node; pkill -9 -f loop_fusion_node
  if [[ $LC == 1 ]]; then cp "$R/traj_lc.txt" "$R/stamped_traj_estimate.txt"; else cp "$R/traj_vio.txt" "$R/stamped_traj_estimate.txt"; fi
elif [[ $BASE == orbslam3 ]]; then
  cp "$CD/orbslam3/${DS}_stereo_inertial.yaml" "$R/config/"; CFG=$R/config/${DS}_stereo_inertial.yaml
  [[ $LC == 1 ]] && sed -i 's/^loopClosing: 0/loopClosing: 1/' "$CFG"
  timeout 900 rosrun sota_tools orbslam3_bag_si /opt/sota/ORB_SLAM3/Vocabulary/ORBvoc.txt "$CFG" "$BAG" "$R" \
      --start-offset "$OFF" --rate "$RATE" > "$R/estimator.log" 2>&1 || status=estimator_failed_rc$?
  # ns EuRoC output (float-printed ns) -> TUM seconds with the exact frame stamps (nearest processed frame)
  python3 - "$R" <<'EOF'
import sys, bisect
R = sys.argv[1]
fr = [l.strip() for l in open(R + '/frames.txt') if l.strip()]
fv = [float(x) for x in fr]
for src, dst in (('traj_world_ns.txt', 'stamped_traj_estimate.txt'), ('traj_upstream_ns.txt', 'traj_upstream.txt')):
    try:
        L = [l.split() for l in open(R + '/' + src) if l.strip()]
    except FileNotFoundError:
        continue
    with open(R + '/' + dst, 'w') as f:
        f.write('# timestamp tx ty tz qx qy qz qw\n')
        for p in L:
            t = float(p[0]) * 1e-9
            i = bisect.bisect_left(fv, t)
            j = min((k for k in (i - 1, i) if 0 <= k < len(fv)), key=lambda k: abs(fv[k] - t))
            assert abs(fv[j] - t) < 1e-5, (t, fv[j])
            f.write('%s %s\n' % (fr[j], ' '.join(p[1:8])))
EOF
else
  echo "unknown method $METHOD"; exit 2
fi
finish
cat "$R/run_info.yaml"
