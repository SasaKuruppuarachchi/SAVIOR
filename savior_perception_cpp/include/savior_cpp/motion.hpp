// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/motion.py: gyro integration, KLT, ego-motion fit, instantaneous GLS test,
// windowed anchor test, log-odds motion tracks (P4) + P7 long window.
#pragma once

#include <map>
#include <optional>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

#include "savior_cpp/calibration.hpp"
#include "savior_cpp/config.hpp"
#include "savior_cpp/types.hpp"

namespace savior {

using Mat3 = cv::Matx33d;
using Vec3 = cv::Vec3d;
using Mat4 = cv::Matx44d;

Mat3 so3_exp(const Vec3 &w);
Vec3 so3_log(const Mat3 &R);

class GyroIntegrator {
 public:
  explicit GyroIntegrator(double max_age_s = 10.0) : max_age_s_(max_age_s) {}
  void add(double t, const Vec3 &w);
  double last_time() const { return t_.empty() ? -Inf : t_.back(); }
  bool covers(double t0, double t1) const { return !t_.empty() && t_.front() <= t0 && t_.back() >= t1; }
  std::optional<Mat3> rotation(double t0, double t1) const;  // R_{I(t0) I(t1)}
  size_t size() const { return t_.size(); }

 private:
  Vec3 omega(double t) const;
  std::vector<double> t_;
  std::vector<Vec3> w_;
  double max_age_s_;
};

struct MotionTrack {
  int id = 0;
  Role role = Role::Unset;
  std::string cls;
  double l = 0;
  bool is_moving = false, is_static = false;
  int missing = 0, n_obs = 0;
  struct Hist {
    int frame;
    double stamp;
    Vec3 P;
  };
  std::vector<Hist> hist;
  MotionInfo last;  // obs + optional ev / win fields
  std::optional<Box> box;
  // P7 raw evidence of the latest frame
  struct Raw {
    bool valid = false;
    double stamp = 0;
    std::optional<InstFit> ev;
    std::optional<WinFit> win, win_long;
    bool matched = false;
  } raw;
  std::string state() const { return is_moving ? "moving" : (is_static ? "static" : "unknown"); }
};

struct EgoMotion {
  Mat3 R = Mat3::eye();
  Vec3 t = Vec3(0, 0, 0);
  double sigma_t = 0, sigma_bg = 0;
  int n_bg = 0, n_inliers = 0;
  bool t_ok = false;
  Vec3 dtheta = Vec3(0, 0, 0);
};

struct MotionStats {
  int n_bg = 0, n_inl = 0;
  bool t_ok = false;
  bool has_ego = false;
  double sigma_bg_px = 0, dtheta_deg = 0, rot_deg = 0;
  Vec3 t = Vec3(0, 0, 0);
  bool gyro = false;
  int n_tracks = 0, n_inst_pts = 0;
  double ms_flow_ego = 0, ms_assoc = 0, ms_points = 0;
};

class MotionEstimator {
 public:
  MotionEstimator(const MotionConfig &cfg, const StereoRectifier &rect, const cv::Mat &static_mask = cv::Mat());
  void reset();
  // returns {instance index: true (moving potential -> root) | false (static -> still / veto)}
  std::map<int, bool> update(const cv::Mat &left, const cv::Mat *right, double stamp, std::vector<Instance> &instances,
                             const std::optional<Mat3> &R_imu);
  // predicted raw px at frame k of static points seen at k-1 (tracker ego model); empty optional = no ego
  bool ego_project(const std::vector<cv::Point2d> &pts, const std::vector<double> &depth,
                   std::vector<cv::Point2d> &out) const;
  const std::optional<EgoMotion> &last_ego() const { return last_ego_; }
  const std::map<int, MotionTrack> &tracks() const { return tracks_; }
  const MotionStats &last_stats() const { return stats_; }
  // debug / equivalence access to the point state prepared for the next frame
  const std::vector<cv::Point2d> &inst_points() const { return in_p_; }
  const std::vector<int> &inst_point_tracks() const { return in_tid_; }
  const std::vector<cv::Point2d> &bg_points() const { return bg_p_; }

  // geometry helpers (public for tests)
  void bearings(const std::vector<cv::Point2d> &pts, int cam, std::vector<Vec3> &b, std::vector<uint8_t> &ok) const;

 private:
  void rect_uv(const std::vector<Vec3> &b, int cam, std::vector<cv::Point2d> &uv, std::vector<uint8_t> &ok) const;
  Vec3 point_from_disparity(const Vec3 &b, double d) const;
  cv::Mat pyr(const cv::Mat &gray) const;
  void klt(const cv::Mat &img0, const cv::Mat &img1, const std::vector<cv::Point2d> &pts, bool fb,
           std::vector<cv::Point2d> &out, std::vector<uint8_t> &ok) const;
  void fb_ok(const cv::Mat &img0, const cv::Mat &img1, const std::vector<cv::Point2d> &p0,
             const std::vector<cv::Point2d> &p1, const std::vector<uint8_t> &ok, std::vector<uint8_t> &res) const;
  EgoMotion estimate_ego(const std::vector<Vec3> &X, const std::vector<Vec3> &b, const Mat3 &R_g, double dt,
                         double gyro_sigma) const;
  struct Group {
    int key;
    std::vector<Vec3> X, b;
  };
  std::map<int, InstFit> instance_fits(const std::vector<Group> &groups, const EgoMotion &ego, double dt) const;
  std::vector<std::optional<Vec3>> anchor_points(const std::vector<const Instance *> &insts) const;
  std::optional<WinFit> window_fit(const MotionTrack &trk, double stamp, double wmin, double wmax) const;
  void observe(MotionTrack &trk, const std::optional<InstFit> &ev, const std::optional<WinFit> &win) const;
  std::vector<cv::Point2d> detect_in_instance(const cv::Mat &img_s, const Instance &inst, int n, int er,
                                              const std::vector<cv::Point2d> &existing) const;
  std::vector<cv::Point2d> detect_background(const cv::Mat &img_s, const std::vector<Box> &boxes,
                                             const std::vector<cv::Point2d> &existing, int n) const;
  void stereo_disp(const cv::Mat &img_l, const cv::Mat *right, const std::vector<cv::Point2d> &pts,
                   std::vector<Vec3> &bl, std::vector<double> &d) const;
  std::vector<Vec3> instance_depth(const std::vector<cv::Point2d> &pts, const std::vector<int> &tids,
                                   const std::map<int, int> &tid_to_inst, const std::vector<Instance> &instances,
                                   const std::vector<Vec3> &b, const std::vector<double> &d_klt) const;

  MotionConfig cfg_;
  const StereoRectifier &rect_;
  double f_raw_;
  Mat3 R_CI_;
  double s_;
  int size_s_w_, size_s_h_;
  cv::Mat static_mask_s_;  // CV_8U 0/1 or empty
  cv::Size win_;
  cv::TermCriteria crit_;
  // state
  cv::Mat prev_pyr_;
  std::optional<double> prev_t_;
  std::vector<cv::Point2d> bg_p_, in_p_;
  std::vector<Vec3> bg_X_, in_X_;
  std::vector<long long> bg_age_;
  std::vector<int> in_tid_;
  std::map<int, MotionTrack> tracks_;  // ordered by id == Python dict insertion order
  int next_id_ = 1;
  std::optional<EgoMotion> last_ego_;
  MotionStats stats_;
  std::map<int, Mat4> poses_;
  int frame_ = 0;
};

double mask_overlap(const Instance &a, const Instance &b);

}  // namespace savior
