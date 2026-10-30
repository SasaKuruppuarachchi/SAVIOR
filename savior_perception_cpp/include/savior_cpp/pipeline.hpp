// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/pipeline.py: segment -> ROI depth -> motion -> gate -> track -> extend -> compose.
#pragma once

#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

#include "savior_cpp/calibration.hpp"
#include "savior_cpp/compose.hpp"
#include "savior_cpp/config.hpp"
#include "savior_cpp/extension.hpp"
#include "savior_cpp/gating.hpp"
#include "savior_cpp/motion.hpp"
#include "savior_cpp/roles.hpp"
#include "savior_cpp/selective.hpp"
#include "savior_cpp/stereo_depth.hpp"
#include "savior_cpp/tracker.hpp"
#include "savior_cpp/types.hpp"

namespace savior {

struct FrameResult {
  double stamp = 0;
  int frame = 0;
  cv::Mat mask_left, mask_right;
  std::vector<Instance> instances;  // detections (with status) + carried
  int n_detections = 0;             // instances[0:n_detections] are this frame's detections
  std::vector<std::pair<int, int>> links;
  std::map<std::string, double> timings_ms;  // depth, motion, gating, tracking, extension, compose, total
  StereoDepth::DepthInfo depth_info;
  std::map<std::string, int> tracks_summary;
  int n_tracks = 0;
  MotionStats motion;
  bool has_motion = false;
  SelectiveStats selective;
  bool has_selective = false;
  long core_px = 0, ext_px = 0;
};

class SaviorPipeline {
 public:
  SaviorPipeline(const PipelineConfig &cfg, const RoleTable &roles, std::shared_ptr<const StereoRectifier> rect,
                 const cv::Mat &static_mask = cv::Mat());
  void reset();
  // left/right: RAW images (gray or BGR). Instances are consumed (moved into the result).
  const FrameResult &process(const cv::Mat &left_raw, const cv::Mat *right_raw, double stamp,
                             std::vector<Instance> instances, const std::optional<Mat3> &R_imu);
  const FrameResult &last() const { return res_; }
  const PipelineConfig &config() const { return cfg_; }
  const RoleTable &roles() const { return roles_; }
  const MotionEstimator *motion() const { return motion_.get(); }
  // JSON of the stats dict of the Python pipeline (keys and layout of SaviorPipeline.process stats)
  std::string stats_json(bool compact, const std::string &timing_extra = "", const std::string &stamp_json = "",
                         const std::string &top_extra = "") const;

 private:
  std::pair<double, double> band(const Instance &inst) const;
  void set_depth(Instance &inst, double d, int n) const;
  PipelineConfig cfg_;
  RoleTable roles_;
  std::shared_ptr<const StereoRectifier> rect_;
  std::unique_ptr<StereoDepth> depth_;
  std::unique_ptr<MotionEstimator> motion_;
  std::unique_ptr<PromotionGate> gate_;
  std::unique_ptr<SelectivePolicy> selective_;
  std::unique_ptr<MaskTracker> tracker_;
  std::unique_ptr<MaskExtender> extender_;
  std::unique_ptr<RightWarper> warper_;
  int frame_index_ = 0;
  FrameResult res_;
};

cv::Mat to_gray(const cv::Mat &img);

}  // namespace savior
