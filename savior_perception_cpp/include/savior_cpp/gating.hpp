// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/gating.py (promotion through interaction, BFS fixpoint, P7 selective branch).
#pragma once

#include <map>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

#include "savior_cpp/config.hpp"
#include "savior_cpp/roles.hpp"
#include "savior_cpp/types.hpp"

namespace savior {

struct GatingResult {
  std::vector<int> roots;
  std::set<int> promoted;
  std::map<int, int> parent;  // child -> parent (sorted = Python sorted(parent.items()))
  std::vector<std::pair<int, int>> links() const { return {parent.begin(), parent.end()}; }
};

// selective context (selective.update output)
struct SelectiveContext {
  std::map<int, std::string> labels;  // instance index -> moving | static | history | unknown
  bool converged = false;
  std::set<std::string> prior;
  bool unknown_promotes = false;
  bool comotion = false;
  double comotion_q = 3.0, comotion_v_min = 0.3;
};

class PromotionGate {
 public:
  PromotionGate(const GatingConfig &cfg, const RoleTable *roles, double fb /* <= 0: no stereo */, double sigma_d_px);
  // evidence: instance index -> true (moving: root) / false (static: still / veto); absent = no evidence
  GatingResult run(std::vector<Instance> &instances, const std::map<int, bool> &evidence,
                   const SelectiveContext *sel) const;
  static GatingResult promote_all(std::vector<Instance> &instances);
  double link_threshold(const Instance &p, const Instance &q) const;
  bool depth_compatible(const Instance &p, const Instance &q) const;
  std::optional<std::pair<double, double>> contact_depths(const Instance &p, const Instance &q) const;
  static bool comotion_refuses(const Instance &p, const Instance &q, const SelectiveContext *sel);

 private:
  struct Dil {
    Box box;
    cv::Mat crop;
  };
  Dil dilated(const Instance &inst) const;
  static long overlap_px(const Dil &a, const Dil &b);
  void bfs(std::vector<Instance> &instances, GatingResult &res, const std::vector<int> &sources,
           const std::vector<int> &candidates, std::map<int, int> &hops, const SelectiveContext *sel) const;
  GatingResult run_selective(std::vector<Instance> &instances, const std::map<int, bool> &evidence,
                             const SelectiveContext &sel) const;
  double half_extent(const std::string &cls) const;
  GatingConfig cfg_;
  const RoleTable *roles_;
  double fb_;
  double sigma_d_px_;
};

}  // namespace savior
