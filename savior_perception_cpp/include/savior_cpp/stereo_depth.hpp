// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/stereo_depth.py (ROI SGBM on rectified crops remapped from the raw images).
#pragma once

#include <array>
#include <optional>
#include <vector>

#include <opencv2/calib3d.hpp>
#include <opencv2/core.hpp>

#include "savior_cpp/calibration.hpp"
#include "savior_cpp/config.hpp"
#include "savior_cpp/types.hpp"

namespace savior {

class StereoDepth {
 public:
  StereoDepth(const StereoRectifier &rect, const DepthConfig &cfg);
  double fb() const { return rect_.fb(); }
  // (u0, v0, u1, v1) in the low-res rectified frame, or nullopt
  std::optional<std::array<int, 4>> raw_box_to_rect_low(const Box &box, int n = 12) const;
  struct DepthInfo {
    int n_rois = 0;
    long matched_px = 0;
  };
  DepthInfo compute(const cv::Mat &left_gray, const cv::Mat &right_gray, const std::vector<Box> &raw_boxes);
  cv::Mat raw_disparity(const Box &box) const;  // CV_32F crop of `box`, 0 = invalid
  std::pair<double, int> robust_disparity(const cv::Mat &mask_crop, const cv::Mat &disp_crop) const;
  int num_disp = 16;
  std::vector<std::array<int, 4>> rois_low;

 private:
  std::vector<std::array<int, 5>> plan_rois(const std::vector<Box> &raw_boxes) const;
  const StereoRectifier &rect_;
  DepthConfig cfg_;
  int s_ = 2;
  cv::Mat map_l_[2], map_r_[2], r2r_low_[2];
  int low_w_ = 0, low_h_ = 0;
  cv::Ptr<cv::StereoMatcher> matcher_;
  cv::Mat disp_low_;
};

}  // namespace savior
