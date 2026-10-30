// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 The SAVIOR authors
// C++ port of savior_perception/core/types.py (plain data types, no ROS).
#pragma once

#include <cmath>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

namespace savior {

constexpr double NaN = std::numeric_limits<double>::quiet_NaN();
constexpr double Inf = std::numeric_limits<double>::infinity();

// Mask layer values (docs/INTERFACE.md 3.1)
constexpr uint8_t MASK_KEEP = 0;
constexpr uint8_t MASK_EXTENSION = 192;
constexpr uint8_t MASK_CORE = 255;

enum class Role { Dynamic, Potential, Static, Ignore, Unset };
enum class Status { None, Root, Promoted, Held, Carried, Unpromoted, Static, Still, Uncertain };

const char *role_name(Role r);
Role role_from_name(const std::string &s);  // throws on unknown
const char *status_name(Status s);
inline bool is_dynamic_status(Status s) {
  return s == Status::Root || s == Status::Promoted || s == Status::Held || s == Status::Carried ||
         s == Status::Uncertain;
}

struct Box {
  int x0 = 0, y0 = 0, x1 = 0, y1 = 0;  // x1/y1 exclusive
  bool operator==(const Box &o) const { return x0 == o.x0 && y0 == o.y0 && x1 == o.x1 && y1 == o.y1; }
  bool operator!=(const Box &o) const { return !(*this == o); }
  int w() const { return x1 - x0; }
  int h() const { return y1 - y0; }
  cv::Rect rect() const { return cv::Rect(x0, y0, std::max(0, x1 - x0), std::max(0, y1 - y0)); }
};

std::optional<Box> mask_bbox(const cv::Mat &mask);  // tight bbox of a CV_8U 0/1 mask
Box clip_box(double x0, double y0, double x1, double y1, int width, int height);
Box expand_box(const Box &b, int pad, double ratio, int width, int height);
long box_area(const Box &b);
std::optional<Box> box_intersection(const Box &a, const Box &b);
double box_iou(const Box &a, const Box &b);

// windowed anchor velocity (motion.window_fit) used by the co-motion gate
struct WinFit {
  double v_rad = 0, s_rad = 0, v_lat = 0, s_lat = 0, dt = 0;
  double V[3] = {0, 0, 0};
  double ur[3] = {0, 0, 0};
};

// instantaneous GLS fit (motion.instance_fits)
struct InstFit {
  int n = 0;
  double rng = 0, speed = 0, m2 = 0;
  double v[3] = {0, 0, 0};
  double cov[4] = {0, 0, 0, 0};
};

// inst.motion summary dict of the Python implementation (only the fields that exist are set)
struct MotionInfo {
  int id = -1;
  std::string state;  // moving | static | unknown
  double l = 0;       // rounded to 2 decimals like Python
  std::string obs;    // none | moving | static | contra | uncertain
  bool has_ev = false;
  double speed = 0, q = 0, rng = 0;
  int n = 0;
  bool has_win = false;
  double w_lat = 0, w_slat = 0, w_rad = 0, w_srad = 0;
  bool dup = false;
  std::string sel, sel_obs;  // P7 selective label / observation
};

struct Instance {
  cv::Mat mask;  // full-frame CV_8U, values 0/1
  std::string cls;
  double score = 1.0;
  Box bbox;
  Role role = Role::Unset;
  // filled by the pipeline
  double disparity = NaN, depth = NaN, sigma_z = NaN;
  int n_depth_px = 0;
  Status status = Status::None;
  int parent = -1;
  int track_id = -1;
  std::optional<MotionInfo> motion;
  std::optional<Box> work_box, depth_box;
  cv::Mat disp_crop;  // CV_32F crop of work_box (empty = None)
  std::optional<WinFit> win;

  Instance() = default;
  // bbox == nullptr -> tight bbox of the mask; else clipped to the image (types.Instance.__post_init__)
  Instance(cv::Mat mask_, std::string cls_, double score_, const Box *bbox_);
  int height() const { return mask.rows; }
  int width() const { return mask.cols; }
  long area() const;  // mask pixels inside bbox
  cv::Mat crop(const Box &b) const { return mask(b.rect()); }
  cv::Mat crop() const { return mask(bbox.rect()); }
  bool is_dynamic() const { return is_dynamic_status(status); }
};

// float32 median exactly as numpy (partition + float32 mean of the two middle values)
float median_f32(std::vector<float> &v);
double median_f64(std::vector<double> &v);
inline double py_round(double x) { return std::nearbyint(x); }          // Python round()/np.rint (half to even)
double round_ndigits(double x, int nd);                                   // Python round(x, nd)

}  // namespace savior
