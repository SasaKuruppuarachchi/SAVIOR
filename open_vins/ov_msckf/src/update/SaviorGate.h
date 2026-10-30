/*
 * OpenVINS: An Open Platform for Visual-Inertial Research
 * Copyright (C) 2018-2023 Patrick Geneva
 * Copyright (C) 2018-2023 Guoquan Huang
 * Copyright (C) 2018-2023 OpenVINS Contributors
 * Copyright (C) 2026 The SAVIOR authors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#ifndef OV_MSCKF_SAVIOR_GATE_H
#define OV_MSCKF_SAVIOR_GATE_H

#include "UpdaterOptions.h"
#include "feat/Feature.h"
#include "utils/print.h"

#include <algorithm>
#include <boost/math/distributions/chi_squared.hpp>
#include <cmath>
#include <cstdint>
#include <deque>
#include <limits>
#include <map>
#include <string>
#include <vector>

namespace ov_msckf {

/**
 * @brief SAVIOR: per-feature scaling of the chi2 gate of an updater (both off by default).
 *
 * The stock test `chi2 > chi2_multipler * chi2_{0.95}(dof)` becomes `chi2 > chi2_multipler * s_sem * s_nis * chi2_{0.95}(dof)`:
 *
 * - **Semantic gate (SAVIOR-SG, `semantic_gate`)**: s_sem from the semantic labels of the feature's observations
 *   (Feature::sem_*, written by the tracker from the SAVIOR mask): background 1 (stock gate), movable-static
 *   `sg_mult_static`, band `sg_mult_band`; the tightest label present wins, unlabelled features get 1.
 * - **NIS-adaptive gate (`nis_gate`)**: s_nis = lambda, the scalar innovation-covariance scale of innovation-based adaptive
 *   estimation (Mehra 1970; Mohamed & Schwarz 1999), estimated robustly as the median over the last `nis_window` chi2 tests
 *   of the NIS normalized by its median under consistency, chi2 / chi2_{0.5}(dof). A consistent filter gives lambda = 1 for
 *   any outlier share below 50 %. The statistic is collected before gating, so lambda does not feed back on itself.
 *   lambda = 1 until the window is full; it is clamped to [nis_min_scale, nis_max_scale] and refreshed once per update call.
 *
 * With both off, the multiplier is exactly chi2_multipler (the upstream test, bit-identical).
 */
class SaviorGate {

public:
  /// Feature class used for the statistics (tightest label present)
  enum Class { BACKGROUND = 0, MOVABLE_STATIC = 1, BAND = 2 };

  SaviorGate(const UpdaterOptions &options, std::string name) : _options(options), _name(std::move(name)) {}

  /// If any scaling is active
  bool active() const { return _options.semantic_gate || _options.nis_gate; }

  /// Semantic multiplier of a label set (tightest label present; 1 if unlabelled or the semantic gate is off)
  double semantic_scale(uint8_t labels) const {
    if (!_options.semantic_gate)
      return 1.0;
    double m = std::numeric_limits<double>::infinity();
    if (labels & ov_core::Feature::SEM_BACKGROUND)
      m = 1.0;
    if (labels & ov_core::Feature::SEM_MOVABLE_STATIC)
      m = std::min(m, _options.sg_mult_static);
    if (labels & ov_core::Feature::SEM_BAND)
      m = std::min(m, _options.sg_mult_band);
    return std::isinf(m) ? 1.0 : m;
  }

  /// NIS scale of the current update (1 if the NIS gate is off or its window is not full yet)
  double nis_scale() const { return _options.nis_gate ? _lambda : 1.0; }

  /// Full chi2 multiplier of a feature with these labels (chi2_multipler itself when both gates are off)
  double multiplier(uint8_t labels) const {
    double m = _options.chi2_multipler;
    if (_options.semantic_gate)
      m *= semantic_scale(labels);
    if (_options.nis_gate)
      m *= _lambda;
    return m;
  }

  /// Record one chi2 test (for the NIS window and the statistics); no-op when both gates are off
  void record(double chi2, int dof, uint8_t labels, bool rejected) {
    if (!active())
      return;
    Class c = ((labels & ov_core::Feature::SEM_BAND) ? BAND : ((labels & ov_core::Feature::SEM_MOVABLE_STATIC) ? MOVABLE_STATIC : BACKGROUND));
    _n_tested[c]++;
    _n_rejected[c] += rejected ? 1 : 0;
    if (_options.nis_gate && dof > 0)
      _pending.push_back(chi2 / chi2_median(dof));
  }

  /// End of an update call: move the recorded NIS samples into the window, refresh lambda, print a periodic summary
  void commit() {
    if (!active())
      return;
    if (_options.nis_gate) {
      for (double r : _pending)
        _window.push_back(r);
      _pending.clear();
      while ((int)_window.size() > _options.nis_window)
        _window.pop_front();
      if ((int)_window.size() >= _options.nis_window) {
        std::vector<double> v(_window.begin(), _window.end());
        size_t mid = v.size() / 2;
        std::nth_element(v.begin(), v.begin() + mid, v.end());
        double med = v.at(mid);
        if (v.size() % 2 == 0) {
          med = 0.5 * (med + *std::max_element(v.begin(), v.begin() + mid));
        }
        _lambda = std::max(_options.nis_min_scale, std::min(_options.nis_max_scale, med));
      }
    }
    if (++_n_updates % 200 == 0)
      print_summary();
  }

  /// One-line summary of the gate statistics (tested / rejected per class, current lambda)
  void print_summary() const {
    PRINT_INFO("[SAVIOR-GATE]: %s updates=%zu tested bg/static/band=%zu/%zu/%zu rejected=%zu/%zu/%zu nis_lambda=%.4f\n", _name.c_str(),
               _n_updates, _n_tested[0], _n_tested[1], _n_tested[2], _n_rejected[0], _n_rejected[1], _n_rejected[2], nis_scale());
  }

private:
  /// Median of the chi2 distribution with dof degrees of freedom (cached)
  double chi2_median(int dof) {
    auto it = _median_cache.find(dof);
    if (it != _median_cache.end())
      return it->second;
    boost::math::chi_squared dist(dof);
    double med = boost::math::quantile(dist, 0.5);
    _median_cache.insert({dof, med});
    return med;
  }

  /// Options of the owning updater
  const UpdaterOptions &_options;

  /// Name used in the summary
  std::string _name;

  /// Current NIS scale
  double _lambda = 1.0;

  /// NIS samples of the current update and the sliding window
  std::vector<double> _pending;
  std::deque<double> _window;

  /// Cached chi2 medians per dof
  std::map<int, double> _median_cache;

  /// Statistics
  size_t _n_updates = 0;
  size_t _n_tested[3] = {0, 0, 0};
  size_t _n_rejected[3] = {0, 0, 0};
};

} // namespace ov_msckf

#endif // OV_MSCKF_SAVIOR_GATE_H
