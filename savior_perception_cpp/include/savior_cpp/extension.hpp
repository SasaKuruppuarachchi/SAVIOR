// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/extension.py (depth-guided extension band, layer 192).
#pragma once

#include <optional>
#include <utility>

#include "savior_cpp/config.hpp"
#include "savior_cpp/types.hpp"

namespace savior {

class MaskExtender {
 public:
  MaskExtender(const ExtensionConfig &cfg, std::optional<double> f, std::optional<double> fb, double sigma_d_px)
      : cfg_(cfg), f_(f), fb_(fb), sigma_d_px_(sigma_d_px) {}
  Box work_box(const Instance &inst) const;
  Box depth_box(const Instance &inst) const;
  int margin_px(double z) const;
  double band(double z) const;
  std::pair<double, double> disparity_band(double z) const;
  struct Result {
    Box box;
    cv::Mat core, ext, disp;  // core/ext CV_8U 0/1 views/crops of box; disp CV_32F view or empty
    int margin = 0;
  };
  Result extend(const Instance &inst, const Box &box, const cv::Mat &disp_crop) const;

 private:
  ExtensionConfig cfg_;
  std::optional<double> f_, fb_;
  double sigma_d_px_;
};

}  // namespace savior
