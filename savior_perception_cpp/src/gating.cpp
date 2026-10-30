// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/gating.hpp"

#include <cmath>
#include <deque>

#include <opencv2/imgproc.hpp>

namespace savior {

PromotionGate::PromotionGate(const GatingConfig &cfg, const RoleTable *roles, double fb, double sigma_d_px)
    : cfg_(cfg), roles_(roles), fb_(fb), sigma_d_px_(sigma_d_px) {}

double PromotionGate::half_extent(const std::string &cls) const {
  if (!roles_) return cfg_.default_half_extent_m;
  return roles_->half_extent(cls, cfg_.default_half_extent_m);
}

double PromotionGate::link_threshold(const Instance &p, const Instance &q) const {
  if (cfg_.mode == "fixed") return cfg_.fixed_threshold_m;
  const double size = half_extent(p.cls) + half_extent(q.cls);
  const double sp = std::isfinite(p.sigma_z) ? p.sigma_z : 0.0;
  const double sq = std::isfinite(q.sigma_z) ? q.sigma_z : 0.0;
  double noise = cfg_.k_sigma * std::hypot(sp, sq);
  if (cfg_.max_noise_m > 0) noise = std::min(noise, cfg_.max_noise_m);
  double thr = size + noise;
  if (cfg_.max_threshold_m > 0) thr = std::min(thr, cfg_.max_threshold_m);
  return thr;
}

std::optional<std::pair<double, double>> PromotionGate::contact_depths(const Instance &p, const Instance &q) const {
  if (p.disp_crop.empty() || q.disp_crop.empty() || !p.work_box || !q.work_box) return std::nullopt;
  const int gap = 3, band = (int)cfg_.contact_px, r = gap + band;
  const int h = p.height(), w = p.width();
  const Box a = expand_box(p.bbox, r + 1, 0.0, w, h), b = expand_box(q.bbox, r + 1, 0.0, w, h);
  auto reg = box_intersection(a, b);
  if (!reg) return std::nullopt;
  const cv::Rect R = reg->rect();
  cv::Mat mp = p.mask(R).clone(), mq = q.mask(R).clone();
  const cv::Mat k_out = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(2 * r + 1, 2 * r + 1));
  const cv::Mat k_in = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(2 * gap + 1, 2 * gap + 1));
  double out[2];
  for (int side = 0; side < 2; ++side) {
    const cv::Mat &m_self = side == 0 ? mp : mq;
    const cv::Mat &m_other = side == 0 ? mq : mp;
    const Instance &inst = side == 0 ? p : q;
    cv::Mat d_out, d_in;
    cv::dilate(m_other, d_out, k_out);
    cv::dilate(m_other, d_in, k_in);
    const Box &wb = *inst.work_box;
    std::vector<float> d;
    bool any = false;
    for (int y = 0; y < R.height; ++y) {
      const uint8_t *o = d_out.ptr<uint8_t>(y), *in = d_in.ptr<uint8_t>(y), *s = m_self.ptr<uint8_t>(y);
      for (int x = 0; x < R.width; ++x) {
        if (!((o[x] & (uint8_t)~in[x] & s[x]) != 0)) continue;
        any = true;
        const int gx = x + R.x, gy = y + R.y;
        if (gx >= wb.x0 && gx < wb.x1 && gy >= wb.y0 && gy < wb.y1) {
          const float v = inst.disp_crop.at<float>(gy - wb.y0, gx - wb.x0);
          if (v > 0) d.push_back(v);
        }
      }
    }
    if (!any) return std::nullopt;
    if ((long)d.size() < cfg_.contact_min_px) return std::nullopt;
    out[side] = fb_ / (double)median_f32(d);
  }
  return std::make_pair(out[0], out[1]);
}

bool PromotionGate::depth_compatible(const Instance &p, const Instance &q) const {
  if (!(std::isfinite(p.depth) && std::isfinite(q.depth))) return cfg_.unknown_depth_policy == "overlap";
  if (cfg_.link_depth == "contact" && fb_ > 0) {
    auto zc = contact_depths(p, q);
    if (zc) {
      const double zp = zc->first, zq = zc->second;
      const double sp = zp * zp * sigma_d_px_ / fb_, sq = zq * zq * sigma_d_px_ / fb_;
      double noise = cfg_.k_sigma * std::hypot(sp, sq);
      if (cfg_.max_noise_m > 0) noise = std::min(noise, cfg_.max_noise_m);
      return std::abs(zp - zq) < cfg_.contact_margin_m + noise;
    }
    if (cfg_.contact_fallback == "reject") return false;
  }
  return std::abs(p.depth - q.depth) < link_threshold(p, q);
}

PromotionGate::Dil PromotionGate::dilated(const Instance &inst) const {
  const int r = (int)cfg_.dilate_px;
  Dil d;
  d.box = expand_box(inst.bbox, r, 0.0, inst.width(), inst.height());
  cv::Mat crop = inst.crop(d.box).clone();  // np.ascontiguousarray: no parent pixels at the border
  if (r > 0) {
    const cv::Mat k = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(2 * r + 1, 2 * r + 1));
    cv::dilate(crop, d.crop, k);
  } else {
    d.crop = crop.clone();
  }
  return d;
}

long PromotionGate::overlap_px(const Dil &a, const Dil &b) {
  auto in = box_intersection(a.box, b.box);
  if (!in) return 0;
  long n = 0;
  for (int y = in->y0; y < in->y1; ++y) {
    const uint8_t *pa = a.crop.ptr<uint8_t>(y - a.box.y0) - a.box.x0;
    const uint8_t *pb = b.crop.ptr<uint8_t>(y - b.box.y0) - b.box.x0;
    for (int x = in->x0; x < in->x1; ++x) n += (pa[x] & pb[x]) != 0;
  }
  return n;
}

GatingResult PromotionGate::run(std::vector<Instance> &instances, const std::map<int, bool> &evidence,
                                const SelectiveContext *sel) const {
  if (sel) return run_selective(instances, evidence, *sel);
  GatingResult res;
  std::vector<int> potential;
  for (int i = 0; i < (int)instances.size(); ++i) {
    Instance &inst = instances[i];
    inst.parent = -1;
    auto ev = evidence.find(i);
    if (inst.role == Role::Dynamic) {
      if (ev != evidence.end() && ev->second == false) {
        inst.status = Status::Still;
        continue;
      }
      inst.status = Status::Root;
      res.roots.push_back(i);
    } else if (inst.role == Role::Potential) {
      if (ev != evidence.end() && ev->second == true) {
        inst.status = Status::Root;
        res.roots.push_back(i);
      } else {
        inst.status = Status::Unpromoted;
        if (!(ev != evidence.end() && ev->second == false)) potential.push_back(i);
      }
    } else {
      inst.status = Status::Static;
    }
  }
  if (res.roots.empty() || potential.empty() || !cfg_.promote_contact) return res;
  std::map<int, Dil> dil;
  for (int i : res.roots) dil[i] = dilated(instances[i]);
  for (int i : potential) dil[i] = dilated(instances[i]);
  std::deque<int> queue(res.roots.begin(), res.roots.end());
  std::set<int> done(res.roots.begin(), res.roots.end());
  std::map<int, int> hops;
  for (int i : res.roots) hops[i] = 0;
  const int max_depth = (int)cfg_.max_depth;
  while (!queue.empty()) {
    const int q = queue.front();
    queue.pop_front();
    if (max_depth > 0 && hops[q] >= max_depth) continue;
    for (int p : potential) {
      if (done.count(p)) continue;
      if (overlap_px(dil[p], dil[q]) >= cfg_.min_overlap_px && depth_compatible(instances[p], instances[q])) {
        done.insert(p);
        res.promoted.insert(p);
        res.parent[p] = q;
        instances[p].status = Status::Promoted;
        instances[p].parent = q;
        hops[p] = hops[q] + 1;
        queue.push_back(p);
      }
    }
  }
  return res;
}

bool PromotionGate::comotion_refuses(const Instance &p, const Instance &q, const SelectiveContext *sel) {
  if (!sel || !sel->comotion || !p.win || !q.win) return false;
  const double qs = sel->comotion_q, v_min = sel->comotion_v_min;
  const WinFit &wp = *p.win, &wq = *q.win;
  const double *ur = wp.ur;
  auto m2 = [ur](const double V[3], double s_rad, double s_lat) {
    const double vr = V[0] * ur[0] + V[1] * ur[1] + V[2] * ur[2];
    const double l0 = V[0] - vr * ur[0], l1 = V[1] - vr * ur[1], l2 = V[2] - vr * ur[2];
    const double a = vr / std::max(s_rad, 1e-6), sl = std::max(s_lat, 1e-6);
    return a * a + (l0 * l0 + l1 * l1 + l2 * l2) / (sl * sl);
  };
  const double nq = std::sqrt(wq.V[0] * wq.V[0] + wq.V[1] * wq.V[1] + wq.V[2] * wq.V[2]);
  if (nq < v_min || m2(wq.V, wq.s_rad, wq.s_lat) < qs * qs) return false;
  if (m2(wp.V, wp.s_rad, wp.s_lat) >= 4.0) return false;
  const double D[3] = {wp.V[0] - wq.V[0], wp.V[1] - wq.V[1], wp.V[2] - wq.V[2]};
  const double d = m2(D, std::hypot(wp.s_rad, wq.s_rad), std::hypot(wp.s_lat, wq.s_lat));
  return d >= qs * qs;
}

void PromotionGate::bfs(std::vector<Instance> &instances, GatingResult &res, const std::vector<int> &sources,
                        const std::vector<int> &candidates, std::map<int, int> &hops,
                        const SelectiveContext *sel) const {
  if (sources.empty() || candidates.empty() || !cfg_.promote_contact) return;
  std::map<int, Dil> dil;
  for (int i : sources) dil[i] = dilated(instances[i]);
  for (int i : candidates)
    if (!dil.count(i)) dil[i] = dilated(instances[i]);
  std::deque<int> queue(sources.begin(), sources.end());
  std::set<int> done(sources.begin(), sources.end());
  const int max_depth = (int)cfg_.max_depth;
  while (!queue.empty()) {
    const int q = queue.front();
    queue.pop_front();
    if (max_depth > 0 && hops[q] >= max_depth) continue;
    for (int p : candidates) {
      if (done.count(p) || res.promoted.count(p)) continue;
      if (overlap_px(dil[p], dil[q]) >= cfg_.min_overlap_px && depth_compatible(instances[p], instances[q]) &&
          !comotion_refuses(instances[p], instances[q], sel)) {
        done.insert(p);
        res.promoted.insert(p);
        res.parent[p] = q;
        instances[p].status = Status::Promoted;
        instances[p].parent = q;
        hops[p] = hops[q] + 1;
        queue.push_back(p);
      }
    }
  }
}

GatingResult PromotionGate::run_selective(std::vector<Instance> &instances, const std::map<int, bool> &evidence,
                                          const SelectiveContext &sel) const {
  GatingResult res;
  std::vector<int> candidates;
  auto label = [&sel](int i) {
    auto it = sel.labels.find(i);
    return it == sel.labels.end() ? std::string("unknown") : it->second;
  };
  for (int i = 0; i < (int)instances.size(); ++i) {
    Instance &inst = instances[i];
    inst.parent = -1;
    if (inst.role == Role::Dynamic) {
      auto ev = evidence.find(i);
      if (ev != evidence.end() && ev->second == false) {
        inst.status = Status::Still;
        continue;
      }
      inst.status = Status::Root;
      res.roots.push_back(i);
    } else if (inst.role == Role::Potential) {
      const std::string lab = label(i);
      if (lab == "moving") {
        inst.status = Status::Root;
        res.roots.push_back(i);
        continue;
      }
      inst.status = Status::Unpromoted;
      if (!(lab == "static" && sel.converged)) candidates.push_back(i);
    } else {
      inst.status = Status::Static;
    }
  }
  std::map<int, int> hops;
  for (int i : res.roots) hops[i] = 0;
  bfs(instances, res, res.roots, candidates, hops, &sel);
  std::vector<int> uncertain;
  for (int i = 0; i < (int)instances.size(); ++i) {
    Instance &inst = instances[i];
    if (inst.role != Role::Potential || inst.status != Status::Unpromoted) continue;
    const std::string lab = label(i);
    const bool is_prior = sel.prior.count(norm_name(inst.cls)) > 0;
    if (is_prior || ((lab == "static" || lab == "history") && sel.converged)) continue;
    inst.status = Status::Uncertain;
    uncertain.push_back(i);
  }
  if (sel.unknown_promotes && !uncertain.empty()) {
    for (int i : uncertain) hops[i] = 0;
    std::vector<int> rest;
    for (int i : candidates)
      if (instances[i].status == Status::Unpromoted) rest.push_back(i);
    bfs(instances, res, uncertain, rest, hops, &sel);
  }
  return res;
}

GatingResult PromotionGate::promote_all(std::vector<Instance> &instances) {
  GatingResult res;
  for (int i = 0; i < (int)instances.size(); ++i) {
    Instance &inst = instances[i];
    inst.parent = -1;
    if (inst.role == Role::Dynamic) {
      inst.status = Status::Root;
      res.roots.push_back(i);
    } else if (inst.role == Role::Potential) {
      inst.status = Status::Promoted;
      res.promoted.insert(i);
    } else {
      inst.status = Status::Static;
    }
  }
  return res;
}

}  // namespace savior
