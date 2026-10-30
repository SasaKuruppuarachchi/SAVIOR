// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/selective.py (P7 "conservative by default, selective when confident").
#pragma once

#include <map>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "savior_cpp/config.hpp"
#include "savior_cpp/gating.hpp"
#include "savior_cpp/motion.hpp"
#include "savior_cpp/types.hpp"

namespace savior {

struct TrackMemory {
  std::optional<double> run_t0;
  int run_n = 0;
  double last_static_t = -Inf, revoke_t = -Inf, last_masked_t = -Inf, seen_t = -Inf;
  std::string obs, revoke_by;
  std::optional<double> ev_t0;
  double ev_last_t = -Inf;
  double rr = 0.0;
};

struct SelectiveStats {
  bool converged = false;
  std::optional<double> onset_t;
  int n_static = 0, n_labels = 0, n_held = 0;
};

class SelectivePolicy {
 public:
  SelectivePolicy(const SelectiveConfig &cfg, const MotionConfig &mcfg);
  void reset();
  SelectiveContext update(double stamp, std::vector<Instance> &instances, const MotionEstimator *motion);
  int finalize(double stamp, std::vector<Instance> &instances);
  const SelectiveStats &last_stats() const { return stats_; }

 private:
  std::string revokes(const std::optional<InstFit> &ev, const std::optional<WinFit> &w,
                      const std::optional<WinFit> &wl) const;
  bool static_bound(const std::optional<WinFit> &w) const;
  std::string observe(TrackMemory &mem, const MotionTrack::Raw *raw, double stamp);
  bool confirmed(const TrackMemory &mem, double stamp) const;
  bool history_static(const TrackMemory &mem, double stamp) const;
  void update_convergence(double stamp, const MotionEstimator *motion);
  SelectiveConfig cfg_;
  MotionConfig mcfg_;
  std::set<std::string> prior_;
  std::map<int, TrackMemory> mem_;
  std::optional<double> prev_t_;
  int onset_count_ = 0;
  std::optional<double> onset_t_;
  bool converged_ = false;
  SelectiveStats stats_;
};

}  // namespace savior
