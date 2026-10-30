// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/pipeline.hpp"

#include <chrono>
#include <cmath>
#include <stdexcept>

#include <opencv2/imgproc.hpp>

#include "savior_cpp/json.hpp"

namespace savior {

using Clock = std::chrono::steady_clock;
static double ms(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}

cv::Mat to_gray(const cv::Mat &img) {
  if (img.channels() == 1) return img;
  cv::Mat g;
  if (img.channels() == 4) cv::cvtColor(img, g, cv::COLOR_BGRA2GRAY);
  else cv::cvtColor(img, g, cv::COLOR_BGR2GRAY);
  return g;
}

SaviorPipeline::SaviorPipeline(const PipelineConfig &cfg, const RoleTable &roles,
                               std::shared_ptr<const StereoRectifier> rect, const cv::Mat &static_mask)
    : cfg_(cfg), roles_(roles), rect_(std::move(rect)) {
  cfg_.validate();
  const PipelineConfig &c = cfg_;
  if (rect_ && c.depth.enable) depth_ = std::make_unique<StereoDepth>(*rect_, c.depth);
  if (c.motion.enable && rect_) motion_ = std::make_unique<MotionEstimator>(c.motion, *rect_, static_mask);
  gate_ = std::make_unique<PromotionGate>(c.gating, &roles_, rect_ ? rect_->fb() : 0.0, c.depth.sigma_d_px);
  if (c.selective.enable) selective_ = std::make_unique<SelectivePolicy>(c.selective, c.motion);
  if (c.tracker.enable) tracker_ = std::make_unique<MaskTracker>(c.tracker);
  extender_ = std::make_unique<MaskExtender>(c.extension, rect_ ? std::optional<double>(rect_->f) : std::nullopt,
                                             rect_ ? std::optional<double>(rect_->fb()) : std::nullopt,
                                             c.depth.sigma_d_px);
  if (rect_ && c.compose.right_mask) warper_ = std::make_unique<RightWarper>(*rect_, c.compose);
}

void SaviorPipeline::reset() {
  if (tracker_) tracker_->reset();
  if (motion_) motion_->reset();
  if (selective_) selective_->reset();
  frame_index_ = 0;
  res_ = FrameResult();
}

std::pair<double, double> SaviorPipeline::band(const Instance &inst) const {
  if (!rect_ || !(std::isfinite(inst.depth) && inst.depth > 0)) return {0.0, Inf};
  return extender_->disparity_band(inst.depth);
}

void SaviorPipeline::set_depth(Instance &inst, double d, int n) const {
  inst.disparity = d;
  inst.n_depth_px = n;
  if (std::isfinite(d) && d > 0) {
    inst.depth = rect_->fb() / d;
    inst.sigma_z = inst.depth * inst.depth * cfg_.depth.sigma_d_px / rect_->fb();
  } else {
    inst.depth = NaN;
    inst.sigma_z = NaN;
  }
}

const FrameResult &SaviorPipeline::process(const cv::Mat &left_raw, const cv::Mat *right_raw, double stamp,
                                           std::vector<Instance> instances, const std::optional<Mat3> &R_imu) {
  const auto t0 = Clock::now();
  frame_index_ += 1;
  const int h = left_raw.rows, w = left_raw.cols;
  for (auto &inst : instances) {
    if (inst.mask.rows != h || inst.mask.cols != w) throw std::invalid_argument("instance mask size != image size");
    if (inst.role == Role::Unset) inst.role = roles_.role(inst.cls);
  }
  std::vector<int> relevant;
  for (int i = 0; i < (int)instances.size(); ++i)
    if (instances[i].role == Role::Dynamic || instances[i].role == Role::Potential) relevant.push_back(i);
  for (int i : relevant) {
    instances[i].work_box = extender_->work_box(instances[i]);
    instances[i].depth_box = extender_->depth_box(instances[i]);
  }
  // ---- ROI stereo depth
  const bool stereo_ok = depth_ && right_raw;
  const bool depth_active = stereo_ok && !relevant.empty();
  StereoDepth::DepthInfo depth_info;
  cv::Mat lg, rg;
  if (depth_active || motion_) {
    lg = to_gray(left_raw);
    if (right_raw) rg = to_gray(*right_raw);
  }
  if (depth_active) {
    std::vector<Box> boxes;
    for (int i : relevant) boxes.push_back(*instances[i].depth_box);
    depth_info = depth_->compute(lg, rg, boxes);
    for (int i : relevant) {
      Instance &inst = instances[i];
      inst.disp_crop = depth_->raw_disparity(*inst.work_box);
      auto dn = depth_->robust_disparity(inst.mask(inst.work_box->rect()), inst.disp_crop);
      set_depth(inst, dn.first, dn.second);
    }
  }
  const auto t1 = Clock::now();
  // ---- motion evidence + selective labels
  std::map<int, bool> evidence;
  std::optional<SelectiveContext> sel;
  const auto t_m = Clock::now();
  if (motion_) evidence = motion_->update(lg, right_raw ? &rg : nullptr, stamp, instances, R_imu);
  if (selective_) {
    sel = selective_->update(stamp, instances, motion_.get());
    sel->unknown_promotes = cfg_.selective.unknown_promotes;
  }
  const auto t_m1 = Clock::now();
  // ---- promotion
  GatingResult gres;
  if (cfg_.gating.enable) {
    gres = gate_->run(instances, evidence, sel ? &*sel : nullptr);
    if (selective_) selective_->finalize(stamp, instances);
  } else {
    gres = PromotionGate::promote_all(instances);
  }
  const auto t2 = Clock::now();
  // ---- tracking
  std::vector<Instance> carried;
  if (tracker_) {
    EgoFn ego_fn;
    const EgoFn *ego = nullptr;
    if (cfg_.tracker.motion_model == "ego" && motion_ && motion_->last_ego()) {
      const MotionEstimator *m = motion_.get();
      ego_fn = [m](const std::vector<cv::Point2d> &p, const std::vector<double> &z, std::vector<cv::Point2d> &o) {
        return m->ego_project(p, z, o);
      };
      ego = &ego_fn;
    }
    carried = tracker_->update(instances, h, w, ego);
    for (auto &inst : carried) {
      inst.work_box = extender_->work_box(inst);
      if (depth_active) inst.disp_crop = depth_->raw_disparity(*inst.work_box);
    }
  }
  const auto t3 = Clock::now();
  // ---- extension
  const int n_det = (int)instances.size();
  std::vector<Instance> all_inst = std::move(instances);
  for (auto &c : carried) all_inst.push_back(std::move(c));
  std::vector<MaskItem> items;
  const bool band_still = cfg_.motion.still_policy == "band";
  for (auto &inst : all_inst) {
    if (band_still && inst.status == Status::Still) {
      MaskItem it;
      it.box = inst.bbox;
      cv::Mat core = inst.mask(inst.bbox.rect());
      it.core = cv::Mat::zeros(core.size(), CV_8U);
      it.ext = core;
      if (!inst.disp_crop.empty() && inst.work_box) {
        const Box &wb = *inst.work_box;
        it.disp = inst.disp_crop(cv::Rect(it.box.x0 - wb.x0, it.box.y0 - wb.y0, it.box.w(), it.box.h()));
      }
      auto b = band(inst);
      it.d_med = inst.disparity;
      it.d_lo = b.first;
      it.d_hi = b.second;
      items.push_back(it);
      continue;
    }
    if (!inst.is_dynamic()) continue;
    auto r = extender_->extend(inst, *inst.work_box, inst.disp_crop);
    auto b = band(inst);
    MaskItem it;
    it.box = r.box;
    it.core = r.core;
    it.ext = r.ext;
    it.disp = r.disp;
    it.d_med = inst.disparity;
    it.d_lo = b.first;
    it.d_hi = b.second;
    items.push_back(it);
  }
  const std::string &fb_mode = cfg_.compose.right_fallback;
  if (fb_mode != "none" && rect_) {
    bool any = false;
    for (const auto &it : items) any |= !(std::isfinite(it.d_med) && it.d_med > 0);
    if (any) {
      std::vector<double> ds;
      for (int i : relevant) {
        const double d = all_inst[i].disparity;
        if (std::isfinite(d) && d > 0) ds.push_back(d);
      }
      const double d_fb = ds.empty() ? rect_->fb() / cfg_.compose.right_fallback_depth_m : median_f64(ds);
      for (auto &it : items)
        if (!(std::isfinite(it.d_med) && it.d_med > 0)) {
          it.d_med = d_fb;
          it.d_lo = std::max(it.d_lo, 1e-3);
          it.right_band_only = fb_mode == "band";
        }
    }
  }
  const auto t4 = Clock::now();
  // ---- compose
  FrameResult res;
  res.mask_left = compose_left(h, w, items);
  if (warper_ && stereo_ok) res.mask_right = warper_->warp(items);
  else if (right_raw) res.mask_right = cv::Mat::zeros(right_raw->rows, right_raw->cols, CV_8U);
  else res.mask_right = cv::Mat::zeros(h, w, CV_8U);
  const auto t5 = Clock::now();
  res.stamp = stamp;
  res.frame = frame_index_;
  res.n_detections = n_det;
  res.links = gres.links();
  res.timings_ms = {{"depth", ms(t0, t1)},    {"gating", ms(t_m1, t2)},   {"tracking", ms(t2, t3)},
                    {"extension", ms(t3, t4)}, {"compose", ms(t4, t5)}, {"total", ms(t0, t5)}};
  if (motion_) res.timings_ms["motion"] = ms(t_m, t_m1);
  res.depth_info = depth_info;
  if (tracker_) {
    res.tracks_summary = tracker_->summary();
    res.n_tracks = (int)tracker_->tracks().size();
  }
  if (motion_) {
    res.has_motion = true;
    res.motion = motion_->last_stats();
  }
  if (selective_) {
    res.has_selective = true;
    res.selective = selective_->last_stats();
  }
  res.core_px = cv::countNonZero(res.mask_left == MASK_CORE);
  res.ext_px = cv::countNonZero(res.mask_left == MASK_EXTENSION);
  res.instances = std::move(all_inst);
  res_ = std::move(res);
  return res_;
}

static double r3(double v) { return round_ndigits(v, 3); }

std::string SaviorPipeline::stats_json(bool compact, const std::string &timing_extra, const std::string &stamp_json,
                                       const std::string &top_extra) const {
  const FrameResult &r = res_;
  JsonWriter j;
  j.begin_obj();
  if (stamp_json.empty()) j.key("stamp").val(r.stamp);
  else j.key("stamp").raw(stamp_json);
  j.key("frame").val(r.frame);
  j.key("image_size").begin_arr().val(r.mask_left.rows).val(r.mask_left.cols).end_arr();
  j.key("timings_ms").begin_obj();
  for (const char *k : {"depth", "gating", "tracking", "extension", "compose", "total", "motion"}) {
    auto it = r.timings_ms.find(k);
    if (it != r.timings_ms.end()) j.key(k).val(r3(it->second));
  }
  if (!timing_extra.empty()) j.raw(timing_extra);  // node: convert / segment / node_total
  j.end_obj();
  std::map<Role, int> n_role = {{Role::Dynamic, 0}, {Role::Potential, 0}, {Role::Static, 0}, {Role::Ignore, 0}};
  int n_roots = 0, n_prom = 0, n_held = 0, n_carried = 0, n_still = 0, n_unc = 0;
  for (int i = 0; i < r.n_detections; ++i) {
    const Instance &x = r.instances[i];
    n_role[x.role] += 1;
    n_roots += x.status == Status::Root;
    n_prom += x.status == Status::Promoted;
    n_held += x.status == Status::Held;
    n_still += x.status == Status::Still;
    n_unc += x.status == Status::Uncertain;
  }
  for (size_t i = r.n_detections; i < r.instances.size(); ++i) n_carried += r.instances[i].status == Status::Carried;
  j.key("n_instances").val(r.n_detections);
  j.key("n_by_role").begin_obj();
  for (Role ro : {Role::Dynamic, Role::Potential, Role::Static, Role::Ignore}) j.key(role_name(ro)).val(n_role[ro]);
  j.end_obj();
  j.key("n_roots").val(n_roots).key("n_promoted").val(n_prom).key("n_held").val(n_held).key("n_carried").val(n_carried);
  j.key("n_tracks").val(r.n_tracks);
  j.key("tracks").begin_obj();
  for (auto &kv : r.tracks_summary) j.key(kv.first).val(kv.second);
  j.end_obj();
  if (!compact) {
    j.key("links").begin_arr();
    for (auto &l : r.links) j.begin_arr().val(l.first).val(l.second).end_arr();
    j.end_arr();
  }
  j.key("depth").begin_obj().key("n_rois").val(r.depth_info.n_rois).key("matched_px").val(r.depth_info.matched_px).end_obj();
  j.key("core_px").val(r.core_px).key("ext_px").val(r.ext_px);
  if (!compact) {
    j.key("instances").begin_arr();
    for (const auto &x : r.instances) {
      auto f4 = [&j](double v) { if (std::isfinite(v)) j.val(round_ndigits(v, 4)); else j.null(); };
      j.begin_obj();
      j.key("cls").val(x.cls).key("score");
      f4(x.score);
      j.key("role").val(role_name(x.role)).key("status").val(status_name(x.status));
      j.key("bbox").begin_arr().val(x.bbox.x0).val(x.bbox.y0).val(x.bbox.x1).val(x.bbox.y1).end_arr();
      j.key("depth"); f4(x.depth);
      j.key("sigma_z"); f4(x.sigma_z);
      j.key("disparity"); f4(x.disparity);
      j.key("parent").val(x.parent).key("track_id").val(x.track_id);
      if (x.motion) {
        const MotionInfo &m = *x.motion;
        j.key("motion").begin_obj().key("id").val(m.id).key("state").val(m.state).key("l").val(m.l).key("obs").val(m.obs);
        if (m.has_ev) j.key("speed").val(m.speed).key("q").val(m.q).key("n").val(m.n).key("rng").val(m.rng);
        if (m.has_win) j.key("w_lat").val(m.w_lat).key("w_slat").val(m.w_slat).key("w_rad").val(m.w_rad).key("w_srad").val(m.w_srad);
        if (m.dup) j.key("dup").val(true);
        if (!m.sel.empty()) j.key("sel").val(m.sel).key("sel_obs").val(m.sel_obs);
        j.end_obj();
      }
      j.end_obj();
    }
    j.end_arr();
  }
  if (r.has_motion) {
    const MotionStats &m = r.motion;
    j.key("n_still").val(n_still);
    j.key("motion").begin_obj().key("n_bg").val(m.n_bg).key("n_inl").val(m.n_inl).key("t_ok").val(m.t_ok);
    if (m.has_ego) {
      j.key("sigma_bg_px").val(m.sigma_bg_px).key("t").begin_arr().val(m.t[0]).val(m.t[1]).val(m.t[2]).end_arr();
      j.key("dtheta_deg").val(m.dtheta_deg).key("rot_deg").val(m.rot_deg).key("gyro").val(m.gyro);
    }
    j.key("n_tracks").val(m.n_tracks).key("n_inst_pts").val(m.n_inst_pts);
    j.key("ms").begin_obj().key("flow_ego").val(r3(m.ms_flow_ego)).key("assoc").val(r3(m.ms_assoc));
    j.key("points").val(r3(m.ms_points)).end_obj();
    j.end_obj();
  }
  if (r.has_selective) {
    const SelectiveStats &s = r.selective;
    j.key("selective").begin_obj().key("converged").val(s.converged).key("onset_t");
    if (s.onset_t) j.val(*s.onset_t); else j.null();
    j.key("n_static").val(s.n_static).key("n_labels").val(s.n_labels).key("n_held").val(s.n_held);
    j.key("n_uncertain").val(n_unc).end_obj();
  }
  if (!top_extra.empty()) j.raw(top_extra);  // node: "imu": {...}
  j.end_obj();
  return j.str();
}

}  // namespace savior
