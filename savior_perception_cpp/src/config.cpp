// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/config.hpp"

#include <algorithm>
#include <cmath>
#include <sstream>
#include <stdexcept>

namespace savior {
namespace {

enum class FT { Bool, Int, Double, String };
struct Field {
  std::string key;
  FT type;
  void *ptr;
};

#define F_B(sec, obj, name) out.push_back({std::string(sec) + "." #name, FT::Bool, (void *)&(obj).name})
#define F_I(sec, obj, name) out.push_back({std::string(sec) + "." #name, FT::Int, (void *)&(obj).name})
#define F_D(sec, obj, name) out.push_back({std::string(sec) + "." #name, FT::Double, (void *)&(obj).name})
#define F_S(sec, obj, name) out.push_back({std::string(sec) + "." #name, FT::String, (void *)&(obj).name})

std::vector<Field> fields(PipelineConfig &c) {
  std::vector<Field> out;
  {
    auto &o = c.depth;
    const char *s = "depth";
    F_B(s, o, enable); F_I(s, o, downsample); F_D(s, o, min_depth_m); F_I(s, o, max_disparity_px);
    F_S(s, o, matcher); F_I(s, o, block_size); F_I(s, o, uniqueness_ratio); F_I(s, o, speckle_window);
    F_I(s, o, speckle_range); F_D(s, o, sigma_d_px); F_I(s, o, min_valid_px); F_I(s, o, mask_erode_px);
    F_I(s, o, roi_pad_px); F_D(s, o, rect_focal_scale); F_D(s, o, rect_size_scale); F_D(s, o, rect_max_scale);
  }
  {
    auto &o = c.gating;
    const char *s = "gating";
    F_B(s, o, enable); F_S(s, o, mode); F_D(s, o, k_sigma); F_D(s, o, default_half_extent_m);
    F_D(s, o, fixed_threshold_m); F_D(s, o, max_threshold_m); F_I(s, o, dilate_px); F_I(s, o, min_overlap_px);
    F_S(s, o, unknown_depth_policy); F_D(s, o, max_noise_m); F_S(s, o, link_depth); F_I(s, o, contact_px);
    F_I(s, o, contact_min_px); F_D(s, o, contact_margin_m); F_S(s, o, contact_fallback); F_B(s, o, promote_contact);
    F_I(s, o, max_depth);
  }
  {
    auto &o = c.tracker;
    const char *s = "tracker";
    F_B(s, o, enable); F_I(s, o, min_hits); F_I(s, o, max_lost); F_I(s, o, hysteresis_frames); F_S(s, o, iou_type);
    F_D(s, o, iou_min); F_B(s, o, class_agnostic); F_D(s, o, velocity_alpha); F_B(s, o, carry_promoted);
    F_S(s, o, motion_model);
  }
  {
    auto &o = c.extension;
    const char *s = "extension";
    F_B(s, o, enable); F_B(s, o, dilate); F_D(s, o, margin_m); F_I(s, o, min_px); F_I(s, o, max_px); F_B(s, o, grow);
    F_S(s, o, band_mode); F_D(s, o, band_m); F_D(s, o, k_sigma); F_D(s, o, fixed_band_m); F_D(s, o, bbox_expand);
  }
  {
    auto &o = c.compose;
    const char *s = "compose";
    F_B(s, o, right_mask); F_I(s, o, right_close_px); F_S(s, o, right_fallback); F_D(s, o, right_fallback_depth_m);
  }
  {
    auto &o = c.motion;
    const char *s = "motion";
    F_B(s, o, enable); F_D(s, o, image_scale); F_I(s, o, klt_win); F_I(s, o, klt_levels); F_D(s, o, fb_max_px);
    F_I(s, o, bg_points); F_I(s, o, bg_min_inliers); F_I(s, o, bg_exclude_px); F_I(s, o, inst_points);
    F_I(s, o, inst_erode_px); F_B(s, o, per_point_depth); F_I(s, o, min_points); F_D(s, o, redetect_ratio);
    F_I(s, o, min_bbox_px); F_D(s, o, stereo_max_dy_px); F_I(s, o, stereo_refresh); F_I(s, o, stereo_inst_points);
    F_I(s, o, ego_iters); F_D(s, o, sigma_px_min); F_D(s, o, sigma_sys_px); F_D(s, o, sigma_d_px);
    F_D(s, o, gyro_sigma_rad); F_D(s, o, no_imu_sigma_rad); F_D(s, o, max_ego_speed_mps); F_D(s, o, imu_time_offset_s);
    F_D(s, o, depth_rel_sigma); F_D(s, o, window_min_s); F_D(s, o, window_max_s); F_D(s, o, anchor_sigma_px);
    F_D(s, o, anchor_sigma_d_px); F_B(s, o, window_moving_potential); F_B(s, o, window_unveto_potential);
    F_D(s, o, q_move); F_D(s, o, q_static); F_D(s, o, v_move_mps); F_D(s, o, v_move_radial_mps);
    F_D(s, o, v_static_mps); F_D(s, o, v_static_radial_mps); F_B(s, o, radial_static_required); F_D(s, o, l_up);
    F_D(s, o, l_down); F_D(s, o, l_max); F_D(s, o, prior_dynamic); F_D(s, o, prior_potential); F_D(s, o, th_moving);
    F_D(s, o, th_static); F_I(s, o, max_missing); F_D(s, o, dup_overlap); F_S(s, o, still_policy);
    F_B(s, o, use_still); F_B(s, o, promote_moving); F_B(s, o, veto_static); F_S(s, o, static_mask_file);
    F_D(s, o, window_long_s);
  }
  {
    auto &o = c.selective;
    const char *s = "selective";
    F_B(s, o, enable); F_S(s, o, prior_static_classes); F_D(s, o, confirm_s); F_I(s, o, confirm_min_obs);
    F_D(s, o, stale_s); F_D(s, o, revoke_q); F_D(s, o, revoke_v_mps); F_D(s, o, revoke_v_radial_mps);
    F_D(s, o, revoke_hold_s); F_B(s, o, long_static); F_D(s, o, converge_s); F_D(s, o, onset_speed_mps);
    F_I(s, o, onset_frames); F_D(s, o, min_on_s); F_D(s, o, history_s); F_D(s, o, history_max_revoke);
    F_D(s, o, history_tau_s); F_B(s, o, comotion_gate); F_D(s, o, comotion_q); F_D(s, o, comotion_v_min_mps);
    F_B(s, o, unknown_promotes);
  }
  return out;
}

std::string lower(std::string s) {
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char ch) { return std::tolower(ch); });
  return s;
}

void check(bool cond, const std::string &msg) {
  if (!cond) throw std::invalid_argument(msg);
}

}  // namespace

const std::vector<std::string> &PipelineConfig::sections() {
  static const std::vector<std::string> s = {"depth", "gating", "tracker", "extension", "compose", "motion", "selective"};
  return s;
}

std::string param_to_string(const ParamValue &v) {
  if (std::holds_alternative<bool>(v)) return std::get<bool>(v) ? "True" : "False";
  if (std::holds_alternative<int64_t>(v)) return std::to_string(std::get<int64_t>(v));
  if (std::holds_alternative<double>(v)) {
    std::ostringstream o;
    o.precision(17);
    o << std::get<double>(v);
    return o.str();
  }
  return std::get<std::string>(v);
}

std::vector<std::pair<std::string, ParamValue>> PipelineConfig::to_flat() const {
  std::vector<std::pair<std::string, ParamValue>> out;
  auto fs = fields(const_cast<PipelineConfig &>(*this));
  for (auto &f : fs) {
    switch (f.type) {
      case FT::Bool: out.emplace_back(f.key, *(bool *)f.ptr); break;
      case FT::Int: out.emplace_back(f.key, *(int64_t *)f.ptr); break;
      case FT::Double: out.emplace_back(f.key, *(double *)f.ptr); break;
      case FT::String: out.emplace_back(f.key, *(std::string *)f.ptr); break;
    }
  }
  return out;
}

bool PipelineConfig::has_key(const std::string &key) const {
  auto fs = fields(const_cast<PipelineConfig &>(*this));
  for (auto &f : fs)
    if (f.key == key) return true;
  return false;
}

void PipelineConfig::set(const std::string &key, const ParamValue &value) {
  auto fs = fields(*this);
  for (auto &f : fs) {
    if (f.key != key) continue;
    switch (f.type) {
      case FT::Bool: {  // config._coerce(bool)
        bool b;
        if (std::holds_alternative<std::string>(value)) {
          std::string s = lower(std::get<std::string>(value));
          if (s == "true" || s == "1" || s == "yes" || s == "on") b = true;
          else if (s == "false" || s == "0" || s == "no" || s == "off") b = false;
          else throw std::invalid_argument(key + ": expected bool, got '" + std::get<std::string>(value) + "'");
        } else if (std::holds_alternative<bool>(value)) b = std::get<bool>(value);
        else if (std::holds_alternative<int64_t>(value)) b = std::get<int64_t>(value) != 0;
        else b = std::get<double>(value) != 0.0;
        *(bool *)f.ptr = b;
        return;
      }
      case FT::Int: {
        int64_t i;
        if (std::holds_alternative<double>(value)) {
          double d = std::get<double>(value);
          if (std::floor(d) != d) throw std::invalid_argument(key + ": expected int, got " + param_to_string(value));
          i = (int64_t)d;
        } else if (std::holds_alternative<int64_t>(value)) i = std::get<int64_t>(value);
        else if (std::holds_alternative<bool>(value)) i = std::get<bool>(value) ? 1 : 0;
        else i = std::stoll(std::get<std::string>(value));
        *(int64_t *)f.ptr = i;
        return;
      }
      case FT::Double: {
        double d;
        if (std::holds_alternative<double>(value)) d = std::get<double>(value);
        else if (std::holds_alternative<int64_t>(value)) d = (double)std::get<int64_t>(value);
        else if (std::holds_alternative<bool>(value)) d = std::get<bool>(value) ? 1.0 : 0.0;
        else d = std::stod(std::get<std::string>(value));
        *(double *)f.ptr = d;
        return;
      }
      case FT::String: *(std::string *)f.ptr = param_to_string(value); return;
    }
  }
  throw std::invalid_argument("unknown config key '" + key + "'");
}

PipelineConfig PipelineConfig::from_flat(const std::vector<std::pair<std::string, ParamValue>> &flat, bool strict) {
  PipelineConfig cfg;
  for (auto &kv : flat) {
    const std::string sec = kv.first.substr(0, kv.first.find('.'));
    const auto &secs = sections();
    if (std::find(secs.begin(), secs.end(), sec) == secs.end() || !cfg.has_key(kv.first)) {
      if (strict) throw std::invalid_argument("unknown config key '" + kv.first + "'");
      continue;
    }
    cfg.set(kv.first, kv.second);
  }
  cfg.validate();
  return cfg;
}

void PipelineConfig::validate() const {
  const auto &d = depth;
  const auto &g = gating;
  const auto &t = tracker;
  const auto &e = extension;
  check(d.downsample >= 1, "depth.downsample must be >= 1");
  check(d.matcher == "sgbm_3way" || d.matcher == "sgbm" || d.matcher == "bm", "depth.matcher: sgbm_3way|sgbm|bm");
  check(d.block_size % 2 == 1 && d.block_size >= 1, "depth.block_size must be odd");
  check(d.min_depth_m > 0, "depth.min_depth_m must be > 0");
  check(g.mode == "adaptive" || g.mode == "fixed", "gating.mode: adaptive|fixed");
  check(g.unknown_depth_policy == "overlap" || g.unknown_depth_policy == "reject", "gating.unknown_depth_policy: overlap|reject");
  check(t.iou_type == "bbox" || t.iou_type == "mask", "tracker.iou_type: bbox|mask");
  check(t.min_hits >= 1 && t.max_lost >= 0 && t.hysteresis_frames >= 0, "tracker counters");
  check(e.band_mode == "adaptive" || e.band_mode == "fixed", "extension.band_mode: adaptive|fixed");
  check(g.link_depth == "median" || g.link_depth == "contact", "gating.link_depth: median|contact");
  check(compose.right_fallback == "none" || compose.right_fallback == "median" || compose.right_fallback == "band",
        "compose.right_fallback: none|median|band");
  check(g.contact_fallback == "median" || g.contact_fallback == "reject", "gating.contact_fallback: median|reject");
  check(t.motion_model == "pixel_cv" || t.motion_model == "ego", "tracker.motion_model: pixel_cv|ego");
  const auto &m = motion;
  check(0 < m.image_scale && m.image_scale <= 1.0, "motion.image_scale must be in (0, 1]");
  check(m.still_policy == "unmask" || m.still_policy == "band", "motion.still_policy: unmask|band");
  check(0 < m.window_min_s && m.window_min_s <= m.window_max_s, "motion: 0 < window_min_s <= window_max_s");
  check(m.th_static < 0 && 0 < m.th_moving, "motion: th_static < 0 < th_moving");
  check(0 <= e.min_px && e.min_px <= e.max_px, "extension: 0 <= min_px <= max_px");
  const auto &sv = selective;
  check(0 < sv.history_max_revoke && sv.history_max_revoke <= 1 && sv.history_tau_s > 0,
        "selective: 0 < history_max_revoke <= 1, history_tau_s > 0");
  check(sv.confirm_s >= 0 && sv.stale_s > 0 && sv.min_on_s >= 0 && sv.converge_s >= 0,
        "selective: confirm_s, min_on_s, converge_s >= 0 and stale_s > 0");
  check(m.window_long_s <= 0 || m.window_long_s >= m.window_max_s, "motion.window_long_s: <= 0 or >= window_max_s");
}

}  // namespace savior
