// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/types.hpp"

#include <algorithm>
#include <stdexcept>

#include <opencv2/core.hpp>

namespace savior {

const char *role_name(Role r) {
  switch (r) {
    case Role::Dynamic: return "dynamic";
    case Role::Potential: return "potential";
    case Role::Static: return "static";
    case Role::Ignore: return "ignore";
    default: return "";
  }
}

Role role_from_name(const std::string &s) {
  if (s == "dynamic") return Role::Dynamic;
  if (s == "potential") return Role::Potential;
  if (s == "static") return Role::Static;
  if (s == "ignore") return Role::Ignore;
  throw std::invalid_argument("unknown role '" + s + "'");
}

const char *status_name(Status s) {
  switch (s) {
    case Status::Root: return "root";
    case Status::Promoted: return "promoted";
    case Status::Held: return "held";
    case Status::Carried: return "carried";
    case Status::Unpromoted: return "unpromoted";
    case Status::Static: return "static";
    case Status::Still: return "still";
    case Status::Uncertain: return "uncertain";
    default: return "";
  }
}

std::optional<Box> mask_bbox(const cv::Mat &mask) {
  int x0 = mask.cols, x1 = -1, y0 = -1, y1 = -1;
  for (int y = 0; y < mask.rows; ++y) {
    const uint8_t *r = mask.ptr<uint8_t>(y);
    int first = -1, last = -1;
    for (int x = 0; x < mask.cols; ++x)
      if (r[x]) {
        if (first < 0) first = x;
        last = x;
      }
    if (first >= 0) {
      if (y0 < 0) y0 = y;
      y1 = y;
      x0 = std::min(x0, first);
      x1 = std::max(x1, last);
    }
  }
  if (y0 < 0) return std::nullopt;
  return Box{x0, y0, x1 + 1, y1 + 1};
}

Box clip_box(double x0, double y0, double x1, double y1, int width, int height) {
  int a = std::max(0, std::min(width, (int)std::floor(x0)));
  int b = std::max(0, std::min(height, (int)std::floor(y0)));
  int c = std::max(a, std::min(width, (int)std::ceil(x1)));
  int d = std::max(b, std::min(height, (int)std::ceil(y1)));
  return Box{a, b, c, d};
}

Box expand_box(const Box &b, int pad, double ratio, int width, int height) {
  int px = pad + (int)std::ceil(ratio * (b.x1 - b.x0));
  int py = pad + (int)std::ceil(ratio * (b.y1 - b.y0));
  return clip_box(b.x0 - px, b.y0 - py, b.x1 + px, b.y1 + py, width, height);
}

long box_area(const Box &b) { return (long)std::max(0, b.x1 - b.x0) * (long)std::max(0, b.y1 - b.y0); }

std::optional<Box> box_intersection(const Box &a, const Box &b) {
  int x0 = std::max(a.x0, b.x0), y0 = std::max(a.y0, b.y0);
  int x1 = std::min(a.x1, b.x1), y1 = std::min(a.y1, b.y1);
  if (x1 <= x0 || y1 <= y0) return std::nullopt;
  return Box{x0, y0, x1, y1};
}

double box_iou(const Box &a, const Box &b) {
  auto in = box_intersection(a, b);
  if (!in) return 0.0;
  long ia = box_area(*in);
  return (double)ia / (double)(box_area(a) + box_area(b) - ia);
}

Instance::Instance(cv::Mat mask_, std::string cls_, double score_, const Box *bbox_)
    : mask(std::move(mask_)), cls(std::move(cls_)), score(score_) {
  CV_Assert(mask.type() == CV_8UC1);
  if (bbox_ == nullptr) {
    auto bb = mask_bbox(mask);
    bbox = bb ? *bb : Box{0, 0, 0, 0};
  } else {
    bbox = clip_box(bbox_->x0, bbox_->y0, bbox_->x1, bbox_->y1, mask.cols, mask.rows);
  }
}

long Instance::area() const { return box_area(bbox) ? (long)cv::countNonZero(crop()) : 0; }

float median_f32(std::vector<float> &v) {
  const size_t n = v.size();
  if (n == 0) return std::numeric_limits<float>::quiet_NaN();
  const size_t k = n / 2;
  std::nth_element(v.begin(), v.begin() + k, v.end());
  float hi = v[k];
  if (n % 2) return hi;
  float lo = *std::max_element(v.begin(), v.begin() + k);
  volatile float s = lo + hi;  // numpy: float32 sum of the two middle values, then / 2 in float32
  return (float)s / 2.0f;
}

double median_f64(std::vector<double> &v) {
  const size_t n = v.size();
  if (n == 0) return NaN;
  const size_t k = n / 2;
  std::nth_element(v.begin(), v.begin() + k, v.end());
  double hi = v[k];
  if (n % 2) return hi;
  double lo = *std::max_element(v.begin(), v.begin() + k);
  return (lo + hi) / 2.0;
}

double round_ndigits(double x, int nd) {
  // CPython round(x, n) is correctly rounded (via repr); this is exact for the stats use (display only)
  if (!std::isfinite(x)) return x;
  char buf[64];
  std::snprintf(buf, sizeof(buf), "%.*f", nd, x);
  return std::strtod(buf, nullptr);
}

}  // namespace savior
