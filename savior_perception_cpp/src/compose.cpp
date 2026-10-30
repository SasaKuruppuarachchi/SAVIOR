// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/compose.hpp"

#include <cmath>

#include <opencv2/imgproc.hpp>

namespace savior {

cv::Mat compose_left(int h, int w, const std::vector<MaskItem> &items) {
  cv::Mat m = cv::Mat::zeros(h, w, CV_8U);
  for (const auto &it : items) m(it.box.rect()).setTo(MASK_EXTENSION, it.ext);
  for (const auto &it : items) m(it.box.rect()).setTo(MASK_CORE, it.core);
  return m;
}

RightWarper::RightWarper(const StereoRectifier &rect, const ComposeConfig &cfg) : rect_(rect), cfg_(cfg) {}

void RightWarper::warp_points(const std::vector<cv::Point> &g, const std::vector<float> &d,
                              std::vector<cv::Point2d> &out, std::vector<uint8_t> &ok) const {
  const size_t n = g.size();
  out.assign(n, cv::Point2d(0, 0));
  ok.assign(n, 0);
  const cv::Mat &r2rx = rect_.raw_to_rect_x[0], &r2ry = rect_.raw_to_rect_y[0];
  const cv::Mat &mrx = rect_.rect_to_raw_x[1], &mry = rect_.rect_to_raw_y[1];
  const float fcx = (float)rect_.cx, fcy = (float)rect_.cy, ff = (float)rect_.f;
  const cv::Matx33d &R1 = rect_.R_rect[1];
  std::vector<size_t> miss;
  std::vector<cv::Point3d> rays;
  for (size_t i = 0; i < n; ++i) {
    const float u = r2rx.at<float>(g[i].y, g[i].x), v = r2ry.at<float>(g[i].y, g[i].x);
    const float ur = u - d[i];
    const int ui = (int)std::nearbyint(ur), vi = (int)std::nearbyint(v);
    const bool base = d[i] > 0 && u > -1e3f;
    bool o = base && ui >= 0 && ui < rect_.rect_w && vi >= 0 && vi < rect_.rect_h;
    double rx = mrx.at<float>(o ? vi : 0, o ? ui : 0), ry = mry.at<float>(o ? vi : 0, o ? ui : 0);
    o = o && rx > -1e3;
    out[i] = cv::Point2d(rx, ry);
    ok[i] = o;
    if (base && !o) {
      const double a = (double)((ur - fcx) / ff), b = (double)((v - fcy) / ff), c = 1.0;
      // rays @ R1 (row vector): rect-right -> cam1
      const cv::Point3d r(a * R1(0, 0) + b * R1(1, 0) + c * R1(2, 0), a * R1(0, 1) + b * R1(1, 1) + c * R1(2, 1),
                          a * R1(0, 2) + b * R1(1, 2) + c * R1(2, 2));
      if (r.z > 1e-6) {
        miss.push_back(i);
        rays.push_back(r);
      }
    }
  }
  if (!rays.empty()) {
    const auto pr = rect_.cams[1].project(rays);
    for (size_t k = 0; k < miss.size(); ++k) {
      out[miss[k]] = pr[k];
      ok[miss[k]] = 1;
    }
  }
}

std::vector<std::vector<cv::Point>> RightWarper::polygons(const MaskItem &it, const cv::Mat &region) const {
  std::vector<std::vector<cv::Point>> cs;
  if (region.empty()) return {};
  cv::findContours(region.clone(), cs, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_NONE);
  if (cs.empty()) return {};
  const bool has_med = std::isfinite(it.d_med) && it.d_med > 0;
  if (!has_med && it.disp.empty()) return {};
  std::vector<cv::Point> g;
  std::vector<float> d;
  std::vector<size_t> lens;
  const float lo = (float)it.d_lo, hi = (float)it.d_hi, med = (float)it.d_med;
  for (const auto &c : cs) {
    lens.push_back(c.size());
    for (const auto &p : c) {
      g.emplace_back(p.x + it.box.x0, p.y + it.box.y0);
      if (!it.disp.empty()) {
        const float dp = it.disp.at<float>(p.y, p.x);
        d.push_back(has_med ? ((dp >= lo && dp <= hi) ? dp : med) : dp);
      } else {
        d.push_back(med);
      }
    }
  }
  std::vector<cv::Point2d> out;
  std::vector<uint8_t> ok;
  warp_points(g, d, out, ok);
  std::vector<std::vector<cv::Point>> polys;
  size_t start = 0;
  for (size_t n : lens) {
    std::vector<cv::Point> p;
    for (size_t k = start; k < start + n; ++k)
      if (ok[k]) p.emplace_back((int)std::nearbyint(out[k].x), (int)std::nearbyint(out[k].y));
    if (p.size() >= 3) polys.push_back(std::move(p));
    start += n;
  }
  return polys;
}

cv::Mat RightWarper::warp(const std::vector<MaskItem> &items) const {
  cv::Mat m = cv::Mat::zeros(rect_.cams[1].height, rect_.cams[1].width, CV_8U);
  std::vector<std::vector<cv::Point>> ext_polys, core_polys;
  for (const auto &it : items) {
    if (it.right_band_only) {
      auto p = polygons(it, it.core | it.ext);
      ext_polys.insert(ext_polys.end(), p.begin(), p.end());
      continue;
    }
    if (cv::countNonZero(it.ext)) {
      auto p = polygons(it, it.core | it.ext);
      ext_polys.insert(ext_polys.end(), p.begin(), p.end());
    }
    auto p = polygons(it, it.core);
    core_polys.insert(core_polys.end(), p.begin(), p.end());
  }
  // one call per polygon (a multi-polygon fillPoly XORs overlapping polygons); OpenCV 4.11 fill semantics on any OpenCV
  for (const auto &p : ext_polys) fill_poly_cv411(m, p, MASK_EXTENSION);
  for (const auto &p : core_polys) fill_poly_cv411(m, p, MASK_CORE);
  const int r = (int)cfg_.right_close_px;
  if (r > 0 && (!ext_polys.empty() || !core_polys.empty())) {
    cv::morphologyEx(m, m, cv::MORPH_CLOSE, cv::Mat::ones(2 * r + 1, 2 * r + 1, CV_8U));
  }
  return m;
}

}  // namespace savior
