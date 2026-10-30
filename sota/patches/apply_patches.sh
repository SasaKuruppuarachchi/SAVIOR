#!/usr/bin/env bash
# apply_patches.sh <VINS-Fusion dir> <dynaVINS dir> <ORB_SLAM3 dir> : patches applied to the pinned upstream sources
# inside the image build.
# Every change is listed in ../README.md ("Patches"). None changes estimator behaviour except where marked.
set -euo pipefail
VF=$1; DV=$2; OS=$3

# ---------------------------------------------------------------------------------------------------------------
# P1  VINS-Fusion + DynaVINS: OpenCV 4 (Noetic ships 4.2) - removed C API constants -> C++ API equivalents
# ---------------------------------------------------------------------------------------------------------------
cv4() {
  find "$@" \( -name '*.cpp' -o -name '*.cc' -o -name '*.h' -o -name '*.hpp' \) -print0 | xargs -0 sed -i -E \
    -e 's/\bCV_FONT_HERSHEY_SIMPLEX\b/cv::FONT_HERSHEY_SIMPLEX/g' \
    -e 's/\bCV_LOAD_IMAGE_GRAYSCALE\b/cv::IMREAD_GRAYSCALE/g' \
    -e 's/\bCV_AA\b/cv::LINE_AA/g' \
    -e 's/\bCV_GRAY2RGB\b/cv::COLOR_GRAY2RGB/g' \
    -e 's/\bCV_GRAY2BGR\b/cv::COLOR_GRAY2BGR/g' \
    -e 's/\bCV_BGR2GRAY\b/cv::COLOR_BGR2GRAY/g' \
    -e 's/\bCV_RGB2GRAY\b/cv::COLOR_RGB2GRAY/g' \
    -e 's/\bCV_THRESH_BINARY_INV\b/cv::THRESH_BINARY_INV/g' \
    -e 's/\bCV_THRESH_BINARY\b/cv::THRESH_BINARY/g' \
    -e 's/\bCV_ADAPTIVE_THRESH_MEAN_C\b/cv::ADAPTIVE_THRESH_MEAN_C/g' \
    -e 's/\bCV_RETR_CCOMP\b/cv::RETR_CCOMP/g' \
    -e 's/\bCV_CHAIN_APPROX_SIMPLE\b/cv::CHAIN_APPROX_SIMPLE/g' \
    -e 's/\bCV_CALIB_CB_(ADAPTIVE_THRESH|NORMALIZE_IMAGE|FILTER_QUADS|FAST_CHECK)\b/cv::CALIB_CB_\1/g' \
    -e 's/\bCV_TERMCRIT_ITER\b/cv::TermCriteria::MAX_ITER/g' \
    -e 's/\bCV_TERMCRIT_EPS\b/cv::TermCriteria::EPS/g' \
    -e 's/\bCV_SHAPE_RECT\b/cv::MORPH_RECT/g' \
    -e 's/\bCV_SHAPE_CROSS\b/cv::MORPH_CROSS/g'
}
cv4 "$VF" "$DV"
# CV_RGB() macro lives in the (no longer transitively included) C header
for f in $(grep -rl 'CV_RGB(' "$VF" "$DV" --include='*.cc' --include='*.cpp' --include='*.h' || true); do
  sed -i '0,/#include/s//#include <opencv2\/imgproc\/imgproc_c.h>\n#include/' "$f"
done
# P2  C++14 (ROS Noetic / log4cxx / PCL headers need >= C++14)
find "$VF" "$DV" -name CMakeLists.txt -print0 | xargs -0 sed -i 's/-std=c++11/-std=c++14/'
# P3  global_fusion is not used (GPS fusion) -> not built
touch "$VF/global_fusion/CATKIN_IGNORE"
# P4  DynaVINS README step: support files of VINS-Fusion's loop_fusion (only needed by loop_fusion_node)
cp "$VF/support_files/brief_k10L6.bin" "$VF/support_files/brief_pattern.yml" "$DV/support_files/"

# ---------------------------------------------------------------------------------------------------------------
# P5  VINS-Fusion + DynaVINS: per-frame timing log (behaviour-neutral; only active when $SOTA_TIMING_FILE is set)
#     frontend = featureTracker.trackImage (every stereo pair), backend = processImage (every frame pushed to the
#     estimator; with multiple_thread=1 upstream pushes every 2nd frame)
# ---------------------------------------------------------------------------------------------------------------
TIMING_FN='#include <cstdio>\n#include <cstdlib>\n#include <mutex>\nstatic void sota_timing_log(const char *what, double t, double ms) {\n  static std::mutex m; static FILE *f = nullptr; static bool init = false;\n  std::lock_guard<std::mutex> l(m);\n  if (!init) { init = true; const char *p = std::getenv("SOTA_TIMING_FILE"); if (p) { f = std::fopen(p, "w"); if (f) std::fprintf(f, "kind,stamp,ms\\n"); } }\n  if (f) { std::fprintf(f, "%s,%.9f,%.4f\\n", what, t, ms); std::fflush(f); }\n}'
for E in "$VF/vins_estimator/src/estimator/estimator.cpp" "$DV/vins_estimator/estimator/estimator.cpp"; do
  grep -q sota_timing_log "$E" && continue
  sed -i "s|#include \"../utility/visualization.h\"|#include \"../utility/visualization.h\"\n$TIMING_FN|" "$E"
  sed -i 's|//printf("featureTracker time: %f\\n", featureTrackerTime.toc());|sota_timing_log("frontend", t, featureTrackerTime.toc());|' "$E"
  sed -i -E 's|^( *)processImage\(feature.second, feature.first\);|\1{ TicToc sota_t; processImage(feature.second, feature.first); sota_timing_log("backend", feature.first, sota_t.toc()); }|' "$E"
  [[ $(grep -c sota_timing_log "$E") -eq 3 ]] || { echo "timing patch failed on $E"; exit 1; }
done

# ---------------------------------------------------------------------------------------------------------------
# P9  VINS-Fusion: SAVIOR dynamic masks (back-end-agnostic SAVIOR) + deterministic synchronous mode. Every change is
#     behind optional yaml keys (savior_mask_dir, savior_deterministic, ...); without them VINS-Fusion is unchanged.
#     See ../README.md "VINS-Fusion + SAVIOR masks" and vins_fusion_savior_mask.patch (unified diff on top of P1-P5).
# ---------------------------------------------------------------------------------------------------------------
if ! grep -q savior_mask "$VF/vins_estimator/CMakeLists.txt"; then
  patch -p1 -d "$VF" < "$(dirname "$0")/vins_fusion_savior_mask.patch"
fi

# ---------------------------------------------------------------------------------------------------------------
# ORB-SLAM3
# P6  OpenCV >= 4.4 requirement relaxed to 4.2 (Noetic/focal); API used by ORB-SLAM3 is available in 4.2
sed -i 's/find_package(OpenCV 4.4)/find_package(OpenCV 4.2)/; s/OpenCV > 4.4 not found/OpenCV > 4.2 not found/' "$OS/CMakeLists.txt"
# P7  no -march=native (portable image; avoids Eigen alignment mismatches between host CPUs)
find "$OS" -name CMakeLists.txt -print0 | xargs -0 sed -i 's/ -march=native//g'
# P8  SaveTrajectoryEuRoC re-bases the trajectory on the first keyframe's IMU frame (not gravity-aligned). With
#     $ORBSLAM3_SAVE_IN_WORLD set, the rebasing is skipped so poses stay in the gravity-aligned (z-up) map world
#     required by posyaw alignment. Default (unset) = upstream behaviour. Output-only change.
python3 - "$OS/src/System.cc" <<'EOF'
import sys
p = sys.argv[1]; s = open(p).read()
old = "        Twb = vpKFs[0]->GetImuPose();\n    else\n        Twb = vpKFs[0]->GetPoseInverse();\n"
assert s.count(old) >= 1, 'P8 anchor not found'
new = old + "    if (getenv(\"ORBSLAM3_SAVE_IN_WORLD\")) Twb = Sophus::SE3f();  // SAVIOR sota patch P8\n"
s = s.replace(old, new)
open(p, 'w').write(s)
EOF
grep -q '#include <cstdlib>' "$OS/src/System.cc" || sed -i '0,/#include/s//#include <cstdlib>\n#include/' "$OS/src/System.cc"
echo "patches applied"
