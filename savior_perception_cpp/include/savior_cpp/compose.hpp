// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/compose.py (layered left mask + boundary warp into the raw right image).
#pragma once

#include <vector>

#include <opencv2/core.hpp>

#include "savior_cpp/calibration.hpp"
#include "savior_cpp/config.hpp"
#include "savior_cpp/types.hpp"

namespace savior {

struct MaskItem {
  Box box;
  cv::Mat core, ext;  // CV_8U 0/1, size of box
  cv::Mat disp;       // CV_32F raw-domain disparity crop of box, or empty
  double d_med = NaN;
  double d_lo = 0.0, d_hi = Inf;
  bool right_band_only = false;
};

cv::Mat compose_left(int h, int w, const std::vector<MaskItem> &items);

// cv::fillPoly of OpenCV 4.11.0 (one polygon, CV_8UC1, LINE_8, shift 0), vendored: OpenCV <= 4.9 clips polygons that leave
// the image differently, the Python node (cv2 4.11) is the reference (src/fillpoly411.cpp)
void fill_poly_cv411(cv::Mat &img, const std::vector<cv::Point> &pts, uint8_t color);

class RightWarper {
 public:
  RightWarper(const StereoRectifier &rect, const ComposeConfig &cfg);
  void warp_points(const std::vector<cv::Point> &g, const std::vector<float> &d, std::vector<cv::Point2d> &out,
                   std::vector<uint8_t> &ok) const;
  cv::Mat warp(const std::vector<MaskItem> &items) const;

 private:
  std::vector<std::vector<cv::Point>> polygons(const MaskItem &it, const cv::Mat &region) const;
  const StereoRectifier &rect_;
  ComposeConfig cfg_;
};

}  // namespace savior
