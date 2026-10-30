/*
 * OpenVINS: An Open Platform for Visual-Inertial Research
 * Copyright (C) 2018-2023 Patrick Geneva
 * Copyright (C) 2018-2023 Guoquan Huang
 * Copyright (C) 2018-2023 OpenVINS Contributors
 * Copyright (C) 2018-2019 Kevin Eckenhoff
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

#ifndef OV_MSCKF_UPDATER_OPTIONS_H
#define OV_MSCKF_UPDATER_OPTIONS_H

#include "utils/print.h"

namespace ov_msckf {

/**
 * @brief Struct which stores general updater options
 */
struct UpdaterOptions {

  /// What chi-squared multipler we should apply
  double chi2_multipler = 5;

  /// Noise sigma for our raw pixel measurements
  double sigma_pix = 1;

  /// Covariance for our raw pixel measurements
  double sigma_pix_sq = 1;

  /// SAVIOR-SG: semantic chi2 gate, multipliers per feature label (see SaviorGate.h; MSCKF and SLAM features only)
  bool semantic_gate = false;
  double sg_mult_static = 1.0;
  double sg_mult_band = 1.0;

  /// SAVIOR: NIS-adaptive chi2 gate (see SaviorGate.h; MSCKF and SLAM features only)
  bool nis_gate = false;
  int nis_window = 200;
  double nis_min_scale = 0.05;
  double nis_max_scale = 20.0;

  /// Nice print function of what parameters we have loaded
  void print() {
    PRINT_DEBUG("    - chi2_multipler: %.1f\n", chi2_multipler);
    PRINT_DEBUG("    - sigma_pix: %.2f\n", sigma_pix);
    if (semantic_gate)
      PRINT_DEBUG("    - SAVIOR semantic gate: movable-static x%.3f, band x%.3f\n", sg_mult_static, sg_mult_band);
    if (nis_gate)
      PRINT_DEBUG("    - SAVIOR NIS gate: window %d, scale [%.3f, %.3f]\n", nis_window, nis_min_scale, nis_max_scale);
  }
};

} // namespace ov_msckf

#endif // OV_MSCKF_UPDATER_OPTIONS_H