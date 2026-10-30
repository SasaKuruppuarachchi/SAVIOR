// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/tracker.py (mask tracker with carry-over and chain hysteresis).
#pragma once

#include <functional>
#include <map>
#include <optional>
#include <string>
#include <vector>

#include "savior_cpp/config.hpp"
#include "savior_cpp/types.hpp"

namespace savior {

enum class TrackState { Tentative, Confirmed, Lost, Removed };

struct Track {
  int id = 0;
  std::string cls;
  Role role = Role::Unset;
  Box box;
  cv::Mat mask;  // CV_8U 0/1 crop of box
  TrackState state = TrackState::Tentative;
  int hits = 1, last_seen = 0;
  std::optional<int> last_promoted;
  double vel[2] = {0, 0};
  double disparity = NaN, depth = NaN, sigma_z = NaN;
  long area = 0;
  double off_ego[2] = {0, 0};
  bool still = false;
  void center(double &cx, double &cy) const {
    cx = (box.x0 + box.x1) * 0.5;
    cy = (box.y0 + box.y1) * 0.5;
  }
  void shift(int frame, int &dx, int &dy) const;
};

// ego callback: points (raw px at k-1) + rect depth -> predicted raw px at k; returns false if no prediction
using EgoFn = std::function<bool(const std::vector<cv::Point2d> &, const std::vector<double> &, std::vector<cv::Point2d> &)>;

class MaskTracker {
 public:
  explicit MaskTracker(const TrackerConfig &cfg) : cfg_(cfg) {}
  void reset();
  std::vector<Instance> update(std::vector<Instance> &instances, int h, int w, const EgoFn *ego);
  const std::vector<Track> &tracks() const { return tracks_; }
  std::map<std::string, int> summary() const;

 private:
  bool in_hysteresis(const Track &t) const;
  bool carry_eligible(const Track &t) const;
  bool compatible(const Track &t, const Instance &d) const;
  double iou(const Track &t, const Instance &d) const;
  void update_track(Track &t, Instance &d);
  void new_track(Instance &d);
  void absorb_det(Track &t, Instance &d);
  std::optional<Instance> carry(const Track &t, int h, int w) const;
  TrackerConfig cfg_;
  std::vector<Track> tracks_;
  int frame_ = 0, next_id_ = 1;
};

}  // namespace savior
