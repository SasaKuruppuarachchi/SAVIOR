// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/config.py: every field maps 1:1 to the ROS parameter "<section>.<field>".
#pragma once

#include <cstdint>
#include <functional>
#include <map>
#include <string>
#include <variant>
#include <vector>

namespace savior {

using ParamValue = std::variant<bool, int64_t, double, std::string>;

struct DepthConfig {
  bool enable = true;
  int64_t downsample = 2;
  double min_depth_m = 0.4;
  int64_t max_disparity_px = 256;
  std::string matcher = "sgbm_3way";
  int64_t block_size = 5;
  int64_t uniqueness_ratio = 10;
  int64_t speckle_window = 50;
  int64_t speckle_range = 2;
  double sigma_d_px = 1.0;
  int64_t min_valid_px = 20;
  int64_t mask_erode_px = 2;
  int64_t roi_pad_px = 4;
  double rect_focal_scale = 1.0;
  double rect_size_scale = 0.0;
  double rect_max_scale = 2.0;
};

struct GatingConfig {
  bool enable = true;
  std::string mode = "adaptive";
  double k_sigma = 3.0;
  double default_half_extent_m = 0.35;
  double fixed_threshold_m = 2.0;
  double max_threshold_m = 0.0;
  int64_t dilate_px = 4;
  int64_t min_overlap_px = 5;
  std::string unknown_depth_policy = "overlap";
  double max_noise_m = 0.0;
  std::string link_depth = "median";
  int64_t contact_px = 6;
  int64_t contact_min_px = 15;
  double contact_margin_m = 0.30;
  std::string contact_fallback = "median";
  bool promote_contact = true;
  int64_t max_depth = 0;
};

struct TrackerConfig {
  bool enable = true;
  int64_t min_hits = 2;
  int64_t max_lost = 5;
  int64_t hysteresis_frames = 5;
  std::string iou_type = "bbox";
  double iou_min = 0.3;
  bool class_agnostic = false;
  double velocity_alpha = 0.5;
  bool carry_promoted = true;
  std::string motion_model = "pixel_cv";
};

struct MotionConfig {
  bool enable = false;
  double image_scale = 0.5;
  int64_t klt_win = 11;
  int64_t klt_levels = 2;
  double fb_max_px = 0.6;
  int64_t bg_points = 150;
  int64_t bg_min_inliers = 15;
  int64_t bg_exclude_px = 10;
  int64_t inst_points = 25;
  int64_t inst_erode_px = 6;
  bool per_point_depth = false;
  int64_t min_points = 6;
  double redetect_ratio = 0.6;
  int64_t min_bbox_px = 0;
  double stereo_max_dy_px = 1.5;
  int64_t stereo_refresh = 8;
  int64_t stereo_inst_points = 10;
  int64_t ego_iters = 4;
  double sigma_px_min = 0.25;
  double sigma_sys_px = 0.25;
  double sigma_d_px = 0.5;
  double gyro_sigma_rad = 0.002;
  double no_imu_sigma_rad = 0.05;
  double max_ego_speed_mps = 1.5;
  double imu_time_offset_s = 0.0;
  double depth_rel_sigma = 0.5;
  double window_min_s = 0.4;
  double window_max_s = 0.8;
  double anchor_sigma_px = 4.0;
  double anchor_sigma_d_px = 0.6;
  bool window_moving_potential = false;
  bool window_unveto_potential = false;
  double q_move = 4.0;
  double q_static = 3.0;
  double v_move_mps = 0.30;
  double v_move_radial_mps = 0.60;
  double v_static_mps = 0.30;
  double v_static_radial_mps = 0.60;
  bool radial_static_required = true;
  double l_up = 1.5;
  double l_down = 0.25;
  double l_max = 3.0;
  double prior_dynamic = 1.0;
  double prior_potential = -1.0;
  double th_moving = 1.5;
  double th_static = -1.5;
  int64_t max_missing = 5;
  double dup_overlap = 0.7;
  std::string still_policy = "unmask";
  bool use_still = true;
  bool promote_moving = true;
  bool veto_static = true;
  std::string static_mask_file = "";
  double window_long_s = 0.0;
};

struct SelectiveConfig {
  bool enable = false;
  std::string prior_static_classes = "box,pallet";
  double confirm_s = 1.0;
  int64_t confirm_min_obs = 8;
  double stale_s = 0.5;
  double revoke_q = 3.0;
  double revoke_v_mps = 0.25;
  double revoke_v_radial_mps = 0.40;
  double revoke_hold_s = 1.0;
  bool long_static = true;
  double converge_s = 5.0;
  double onset_speed_mps = 0.2;
  int64_t onset_frames = 3;
  double min_on_s = 0.5;
  double history_s = 2.0;
  double history_max_revoke = 0.3;
  double history_tau_s = 1.0;
  bool comotion_gate = true;
  double comotion_q = 3.0;
  double comotion_v_min_mps = 0.3;
  bool unknown_promotes = false;
};

struct ExtensionConfig {
  bool enable = true;
  bool dilate = true;
  double margin_m = 0.10;
  int64_t min_px = 8;
  int64_t max_px = 40;
  bool grow = true;
  std::string band_mode = "adaptive";
  double band_m = 0.25;
  double k_sigma = 2.0;
  double fixed_band_m = 0.5;
  double bbox_expand = 0.10;
};

struct ComposeConfig {
  bool right_mask = true;
  int64_t right_close_px = 0;
  std::string right_fallback = "none";
  double right_fallback_depth_m = 3.0;
};

struct PipelineConfig {
  DepthConfig depth;
  GatingConfig gating;
  TrackerConfig tracker;
  ExtensionConfig extension;
  ComposeConfig compose;
  MotionConfig motion;
  SelectiveConfig selective;

  static const std::vector<std::string> &sections();
  // ordered (section order, field order) flat view {"depth.enable": value, ...}
  std::vector<std::pair<std::string, ParamValue>> to_flat() const;
  // set one key with the coercion rules of config._coerce (throws std::invalid_argument on bad key / value)
  void set(const std::string &key, const ParamValue &value);
  bool has_key(const std::string &key) const;
  void validate() const;  // throws std::invalid_argument like config.validate
  static PipelineConfig from_flat(const std::vector<std::pair<std::string, ParamValue>> &flat, bool strict = true);
};

std::string param_to_string(const ParamValue &v);

}  // namespace savior
