// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/extension.hpp"

#include <cmath>
#include <vector>

#include <opencv2/imgproc.hpp>

namespace savior {

Box MaskExtender::work_box(const Instance &inst) const {
  const int pad = (cfg_.enable && cfg_.dilate) ? (int)cfg_.max_px : 0;
  const double ratio = (cfg_.enable && cfg_.grow) ? cfg_.bbox_expand : 0.0;
  return expand_box(inst.bbox, pad + 1, ratio, inst.width(), inst.height());
}

Box MaskExtender::depth_box(const Instance &inst) const {
  const double ratio = (cfg_.enable && cfg_.grow) ? cfg_.bbox_expand : 0.0;
  return expand_box(inst.bbox, 0, ratio, inst.width(), inst.height());
}

int MaskExtender::margin_px(double z) const {
  if (!f_ || !std::isfinite(z) || z <= 0) return (int)cfg_.min_px;
  return (int)std::nearbyint(std::min(std::max(*f_ * cfg_.margin_m / z, (double)cfg_.min_px), (double)cfg_.max_px));
}

double MaskExtender::band(double z) const {
  if (cfg_.band_mode == "fixed") return cfg_.fixed_band_m;
  const double sz = (fb_ && *fb_ != 0.0) ? (z * z * sigma_d_px_ / *fb_) : 0.0;
  return cfg_.band_m + cfg_.k_sigma * sz;
}

std::pair<double, double> MaskExtender::disparity_band(double z) const {
  const double delta = band(z);
  const double d_lo = *fb_ / (z + delta);
  const double zn = z - delta;
  const double d_hi = zn > 1e-3 ? *fb_ / zn : Inf;
  return {d_lo, d_hi};
}

MaskExtender::Result MaskExtender::extend(const Instance &inst, const Box &box, const cv::Mat &disp_crop) const {
  const ExtensionConfig &c = cfg_;
  const int h = inst.height(), w = inst.width();
  const int margin = (c.enable && c.dilate) ? margin_px(inst.depth) : 0;
  const bool can_grow = c.enable && c.grow && !disp_crop.empty() && fb_ && *fb_ != 0.0 && std::isfinite(inst.depth) &&
                        inst.depth > 0;
  const Box gbox = can_grow ? expand_box(inst.bbox, 0, c.bbox_expand, w, h) : inst.bbox;
  const Box rbox = margin > 0 ? expand_box(inst.bbox, margin + 1, 0.0, w, h) : inst.bbox;
  Box ub{std::min(gbox.x0, rbox.x0), std::min(gbox.y0, rbox.y0), std::max(gbox.x1, rbox.x1), std::max(gbox.y1, rbox.y1)};
  ub = Box{std::max(ub.x0, box.x0), std::max(ub.y0, box.y0), std::min(ub.x1, box.x1), std::min(ub.y1, box.y1)};
  Result r;
  r.box = ub;
  r.core = inst.mask(ub.rect());
  if (!disp_crop.empty())
    r.disp = disp_crop(cv::Rect(ub.x0 - box.x0, ub.y0 - box.y0, ub.x1 - ub.x0, ub.y1 - ub.y0));
  r.ext = cv::Mat::zeros(r.core.size(), CV_8U);
  if (!c.enable) return r;
  r.margin = margin;
  if (margin > 0) {
    cv::Mat notcore = 1 - r.core, dist;  // ~core as 0/1 (bool view) -> distance to the core
    cv::distanceTransform(notcore, dist, cv::DIST_L2, 3);
    cv::Mat ring = dist <= (float)margin;  // 0/255
    r.ext.setTo(1, ring);
  }
  if (can_grow) {
    const auto band = disparity_band(inst.depth);
    const float lo = (float)band.first, hi = (float)band.second;
    cv::Mat cand = cv::Mat::zeros(r.core.size(), CV_8U);
    for (int y = 0; y < cand.rows; ++y)
      for (int x = 0; x < cand.cols; ++x) {
        const float d = r.disp.at<float>(y, x);
        cand.at<uint8_t>(y, x) = d >= lo && d <= hi;
      }
    if (gbox != ub) {
      cv::Mat region = cv::Mat::zeros(cand.size(), CV_8U);
      region(cv::Rect(gbox.x0 - ub.x0, gbox.y0 - ub.y0, gbox.x1 - gbox.x0, gbox.y1 - gbox.y0)).setTo(1);
      cand &= region;
    }
    if (cv::countNonZero(cand)) {
      cv::Mat seeds = cand | r.core, labels;
      const int n = cv::connectedComponents(seeds, labels, 8, CV_32S);
      std::vector<uint8_t> lut(n, 0);
      for (int y = 0; y < labels.rows; ++y)
        for (int x = 0; x < labels.cols; ++x)
          if (r.core.at<uint8_t>(y, x)) lut[labels.at<int>(y, x)] = 1;
      lut[0] = 0;
      for (int y = 0; y < labels.rows; ++y)
        for (int x = 0; x < labels.cols; ++x)
          if (lut[labels.at<int>(y, x)] && cand.at<uint8_t>(y, x)) r.ext.at<uint8_t>(y, x) = 1;
    }
  }
  for (int y = 0; y < r.ext.rows; ++y)
    for (int x = 0; x < r.ext.cols; ++x)
      if (r.core.at<uint8_t>(y, x)) r.ext.at<uint8_t>(y, x) = 0;
  return r;
}

}  // namespace savior
