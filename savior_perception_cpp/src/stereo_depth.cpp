// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/stereo_depth.hpp"

#include <algorithm>
#include <cmath>
#include <set>

#include <opencv2/imgproc.hpp>

namespace savior {

static int ceil16(double x) { return std::max(16, (int)std::ceil(x / 16.0) * 16); }

static cv::Mat subsample(const cv::Mat &m, int s) {
  const int h = (m.rows + s - 1) / s, w = (m.cols + s - 1) / s;
  cv::Mat o(h, w, m.type());
  for (int y = 0; y < h; ++y) {
    const float *src = m.ptr<float>(y * s);
    float *dst = o.ptr<float>(y);
    for (int x = 0; x < w; ++x) dst[x] = src[x * s];
  }
  return o;
}

StereoDepth::StereoDepth(const StereoRectifier &rect, const DepthConfig &cfg) : rect_(rect), cfg_(cfg) {
  s_ = (int)cfg.downsample;
  map_l_[0] = subsample(rect.rect_to_raw_x[0], s_);
  map_l_[1] = subsample(rect.rect_to_raw_y[0], s_);
  map_r_[0] = subsample(rect.rect_to_raw_x[1], s_);
  map_r_[1] = subsample(rect.rect_to_raw_y[1], s_);
  low_h_ = map_l_[0].rows;
  low_w_ = map_l_[0].cols;
  const float sf = (float)s_;
  for (int k = 0; k < 2; ++k) {
    const cv::Mat &src = k == 0 ? rect.raw_to_rect_x[0] : rect.raw_to_rect_y[0];
    r2r_low_[k].create(src.size(), CV_32F);
    const float *a = src.ptr<float>();
    float *b = r2r_low_[k].ptr<float>();
    for (size_t i = 0; i < src.total(); ++i) b[i] = a[i] / sf;
  }
  const double dmax_full = std::min(rect.fb() / cfg.min_depth_m, (double)cfg.max_disparity_px);
  num_disp = ceil16(dmax_full / s_);
  const int bs = (int)cfg.block_size;
  if (cfg.matcher == "bm") {
    auto m = cv::StereoBM::create(num_disp, std::max(5, bs));
    m->setUniquenessRatio((int)cfg.uniqueness_ratio);
    m->setSpeckleWindowSize((int)cfg.speckle_window);
    m->setSpeckleRange((int)cfg.speckle_range);
    m->setTextureThreshold(10);
    matcher_ = m;
  } else {
    const int mode = cfg.matcher == "sgbm_3way" ? cv::StereoSGBM::MODE_SGBM_3WAY : cv::StereoSGBM::MODE_SGBM;
    matcher_ = cv::StereoSGBM::create(0, num_disp, bs, 8 * bs * bs, 32 * bs * bs, 1, 0, (int)cfg.uniqueness_ratio,
                                      (int)cfg.speckle_window, (int)cfg.speckle_range, mode);
  }
  disp_low_ = cv::Mat::zeros(low_h_, low_w_, CV_32F);
}

std::optional<std::array<int, 4>> StereoDepth::raw_box_to_rect_low(const Box &box, int n) const {
  if (box.x1 <= box.x0 || box.y1 <= box.y0) return std::nullopt;
  auto lin = [n](int a, int b) {  // np.unique(np.linspace(a, b, n).astype(np.int32))
    std::set<int> s;
    const double start = a, delta = (double)b - start, div = n - 1, step = delta / div;
    for (int i = 0; i < n; ++i) {
      double y = (step == 0) ? (i / div) * delta : i * step;
      y += start;
      if (i == n - 1) y = b;
      s.insert((int)y);
    }
    return std::vector<int>(s.begin(), s.end());
  };
  const auto xs = lin(box.x0, box.x1 - 1), ys = lin(box.y0, box.y1 - 1);
  float umin = 0, umax = 0, vmin = 0, vmax = 0;
  bool any = false;
  for (int y : ys) {
    const float *pu = r2r_low_[0].ptr<float>(y), *pv = r2r_low_[1].ptr<float>(y);
    for (int x : xs) {
      const float u = pu[x], v = pv[x];
      if (!(u > -1.0e3f)) continue;
      if (!any) {
        umin = umax = u;
        vmin = vmax = v;
        any = true;
      } else {
        umin = std::min(umin, u); umax = std::max(umax, u);
        vmin = std::min(vmin, v); vmax = std::max(vmax, v);
      }
    }
  }
  if (!any) return std::nullopt;
  const int pad = (int)std::ceil((double)cfg_.roi_pad_px / s_);
  int u0 = (int)std::floor((double)umin) - pad;
  int u1 = (int)std::ceil((double)umax) + 1 + pad;
  int v0 = (int)std::floor((double)vmin) - pad;
  int v1 = (int)std::ceil((double)vmax) + 1 + pad;
  u0 = std::max(0, u0); u1 = std::min(low_w_, u1);
  v0 = std::max(0, v0); v1 = std::min(low_h_, v1);
  if (u1 <= u0 || v1 <= v0) return std::nullopt;
  return std::array<int, 4>{u0, v0, u1, v1};
}

std::vector<std::array<int, 5>> StereoDepth::plan_rois(const std::vector<Box> &raw_boxes) const {
  std::vector<std::array<int, 5>> rois;
  const int bs = (int)cfg_.block_size;
  for (const auto &b : raw_boxes) {
    auto rb = raw_box_to_rect_low(b);
    if (!rb) continue;
    int u0 = (*rb)[0], v0 = (*rb)[1], u1 = (*rb)[2], v1 = (*rb)[3];
    const int xe = std::max(0, u0 - num_disp);
    if (u1 - xe < num_disp + bs + 1) u1 = std::min(low_w_, xe + num_disp + bs + 1);
    if (v1 - v0 < bs + 2) continue;
    rois.push_back({xe, v0, u1, v1, u0});
  }
  auto area = [](const std::array<int, 5> &r) { return (long)(r[2] - r[0]) * (r[3] - r[1]); };
  bool merged = true;
  while (merged && rois.size() > 1) {
    merged = false;
    for (size_t i = 0; i < rois.size() && !merged; ++i)
      for (size_t j = i + 1; j < rois.size(); ++j) {
        const auto a = rois[i], b = rois[j];
        if (a[0] >= b[2] || b[0] >= a[2] || a[1] >= b[3] || b[1] >= a[3]) continue;
        std::array<int, 5> u = {std::min(a[0], b[0]), std::min(a[1], b[1]), std::max(a[2], b[2]), std::max(a[3], b[3]),
                                std::min(a[4], b[4])};
        if (area(u) <= area(a) + area(b)) {
          rois[i] = u;
          rois.erase(rois.begin() + j);
          merged = true;
          break;
        }
      }
  }
  return rois;
}

StereoDepth::DepthInfo StereoDepth::compute(const cv::Mat &left_gray, const cv::Mat &right_gray,
                                            const std::vector<Box> &raw_boxes) {
  disp_low_.setTo(0.0f);
  auto rois = plan_rois(raw_boxes);
  rois_low.clear();
  long px = 0;
  const float scale = (float)(s_ / 16.0);
  for (const auto &r : rois) {
    const int x0 = r[0], y0 = r[1], x1 = r[2], y1 = r[3], xk = r[4];
    rois_low.push_back({x0, y0, x1, y1});
    const cv::Rect sl(x0, y0, x1 - x0, y1 - y0);
    cv::Mat lc, rc, d16;
    cv::remap(left_gray, lc, map_l_[0](sl), map_l_[1](sl), cv::INTER_LINEAR, cv::BORDER_CONSTANT, cv::Scalar(0));
    cv::remap(right_gray, rc, map_r_[0](sl), map_r_[1](sl), cv::INTER_LINEAR, cv::BORDER_CONSTANT, cv::Scalar(0));
    matcher_->compute(lc, rc, d16);
    const int k = xk - x0;
    for (int y = 0; y < d16.rows; ++y) {
      const int16_t *src = d16.ptr<int16_t>(y);
      float *dst = disp_low_.ptr<float>(y0 + y);
      for (int x = k; x < d16.cols; ++x) dst[x0 + x] = src[x] <= 0 ? 0.0f : (float)src[x] * scale;
    }
    px += (long)lc.total();
  }
  return DepthInfo{(int)rois.size(), px};
}

cv::Mat StereoDepth::raw_disparity(const Box &box) const {
  cv::Mat out;
  const cv::Rect r = box.rect();
  if (r.area() == 0) return cv::Mat::zeros(std::max(0, box.h()), std::max(0, box.w()), CV_32F);
  cv::remap(disp_low_, out, r2r_low_[0](r), r2r_low_[1](r), cv::INTER_NEAREST, cv::BORDER_CONSTANT, cv::Scalar(0));
  return out;
}

std::pair<double, int> StereoDepth::robust_disparity(const cv::Mat &mask_crop, const cv::Mat &disp_crop) const {
  std::vector<float> vals;
  if (cfg_.mask_erode_px > 0) {
    cv::Mat er;
    // numpy slices reach OpenCV without their parent matrix: copy so the filter border is the crop border
    cv::erode(mask_crop.clone(), er, cv::Mat::ones(3, 3, CV_8U), cv::Point(-1, -1), (int)cfg_.mask_erode_px);
    for (int y = 0; y < er.rows; ++y) {
      const uint8_t *m = er.ptr<uint8_t>(y);
      const float *d = disp_crop.ptr<float>(y);
      for (int x = 0; x < er.cols; ++x)
        if (m[x] && d[x] > 0) vals.push_back(d[x]);
    }
    if ((long)vals.size() >= cfg_.min_valid_px) {
      int n = (int)vals.size();
      return {(double)median_f32(vals), n};
    }
  }
  vals.clear();
  for (int y = 0; y < mask_crop.rows; ++y) {
    const uint8_t *m = mask_crop.ptr<uint8_t>(y);
    const float *d = disp_crop.ptr<float>(y);
    for (int x = 0; x < mask_crop.cols; ++x)
      if (m[x] && d[x] > 0) vals.push_back(d[x]);
  }
  const int n = (int)vals.size();
  if (n < std::max<long>(1, cfg_.min_valid_px)) return {NaN, n};
  return {(double)median_f32(vals), n};
}

}  // namespace savior
