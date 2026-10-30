// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/tracker.hpp"

#include <algorithm>
#include <cmath>
#include <set>
#include <tuple>

namespace savior {

void Track::shift(int frame, int &dx, int &dy) const {
  const double n = (double)(frame - last_seen);
  dx = (int)std::nearbyint(off_ego[0] + vel[0] * n);
  dy = (int)std::nearbyint(off_ego[1] + vel[1] * n);
}

static Box shift_box(const Box &b, int dx, int dy) { return Box{b.x0 + dx, b.y0 + dy, b.x1 + dx, b.y1 + dy}; }

void MaskTracker::reset() {
  tracks_.clear();
  frame_ = 0;
  next_id_ = 1;
}

bool MaskTracker::compatible(const Track &t, const Instance &d) const {
  if (cfg_.class_agnostic) {
    auto dp = [](Role r) { return r == Role::Dynamic || r == Role::Potential; };
    return t.role == d.role || (dp(t.role) && dp(d.role));
  }
  return t.cls == d.cls;
}

double MaskTracker::iou(const Track &t, const Instance &d) const {
  int dx, dy;
  t.shift(frame_, dx, dy);
  const Box pbox = shift_box(t.box, dx, dy);
  if (cfg_.iou_type == "bbox") return box_iou(pbox, d.bbox);
  auto in = box_intersection(pbox, d.bbox);
  if (!in) return 0.0;
  long i = 0;
  for (int y = in->y0; y < in->y1; ++y)
    for (int x = in->x0; x < in->x1; ++x)
      i += t.mask.at<uint8_t>(y - pbox.y0, x - pbox.x0) && d.mask.at<uint8_t>(y, x);
  const long u = t.area + d.area() - i;
  return u > 0 ? (double)i / (double)u : 0.0;
}

std::vector<Instance> MaskTracker::update(std::vector<Instance> &instances, int h, int w, const EgoFn *ego) {
  frame_ += 1;
  const int f = frame_;
  if (ego && cfg_.motion_model == "ego" && !tracks_.empty()) {
    std::vector<cv::Point2d> c_prev;
    std::vector<double> z;
    for (const auto &t : tracks_) {
      double cx, cy;
      t.center(cx, cy);
      const double n = (double)(f - 1 - t.last_seen);
      c_prev.emplace_back((cx + t.off_ego[0]) + t.vel[0] * n, (cy + t.off_ego[1]) + t.vel[1] * n);
      z.push_back(t.depth);
    }
    std::vector<cv::Point2d> pred;
    if ((*ego)(c_prev, z, pred)) {
      for (size_t k = 0; k < tracks_.size(); ++k)
        if (std::isfinite(pred[k].x) && std::isfinite(pred[k].y)) {
          tracks_[k].off_ego[0] = tracks_[k].off_ego[0] + (pred[k].x - c_prev[k].x);
          tracks_[k].off_ego[1] = tracks_[k].off_ego[1] + (pred[k].y - c_prev[k].y);
        }
    }
  }
  std::vector<int> dets;
  for (int i = 0; i < (int)instances.size(); ++i)
    if (instances[i].role == Role::Dynamic || instances[i].role == Role::Potential) dets.push_back(i);
  using PairT = std::tuple<double, int, int, int>;  // (iou, -id, ti, di)
  std::vector<PairT> pairs;
  for (int ti = 0; ti < (int)tracks_.size(); ++ti)
    for (int di : dets) {
      if (!compatible(tracks_[ti], instances[di])) continue;
      const double v = iou(tracks_[ti], instances[di]);
      if (v >= cfg_.iou_min) pairs.emplace_back(v, -tracks_[ti].id, ti, di);
    }
  std::sort(pairs.begin(), pairs.end(), [](const PairT &a, const PairT &b) { return a > b; });
  std::set<int> t_used, d_used;
  for (const auto &p : pairs) {
    const int ti = std::get<2>(p), di = std::get<3>(p);
    if (t_used.count(ti) || d_used.count(di)) continue;
    t_used.insert(ti);
    d_used.insert(di);
    update_track(tracks_[ti], instances[di]);
  }
  for (int di : dets)
    if (!d_used.count(di)) new_track(instances[di]);
  std::vector<Instance> carried;
  for (int ti = 0; ti < (int)tracks_.size(); ++ti) {
    Track &trk = tracks_[ti];
    if (t_used.count(ti) || trk.last_seen == f) continue;
    if (trk.state == TrackState::Tentative) {
      trk.state = TrackState::Removed;
      continue;
    }
    if (f - trk.last_seen > cfg_.max_lost) {
      trk.state = TrackState::Removed;
      continue;
    }
    trk.state = TrackState::Lost;
    if (carry_eligible(trk)) {
      auto inst = carry(trk, h, w);
      if (inst) carried.push_back(std::move(*inst));
    }
  }
  tracks_.erase(std::remove_if(tracks_.begin(), tracks_.end(),
                               [](const Track &t) { return t.state == TrackState::Removed; }),
                tracks_.end());
  return carried;
}

bool MaskTracker::in_hysteresis(const Track &t) const {
  return t.last_promoted && frame_ - *t.last_promoted <= cfg_.hysteresis_frames;
}

bool MaskTracker::carry_eligible(const Track &t) const {
  if (t.still) return false;
  if (t.role == Role::Dynamic) return true;
  return cfg_.carry_promoted && in_hysteresis(t);
}

void MaskTracker::update_track(Track &trk, Instance &det) {
  const int f = frame_;
  const int dt = std::max(1, f - trk.last_seen);
  double ox, oy;
  trk.center(ox, oy);
  trk.box = det.bbox;
  trk.mask = det.crop().clone();
  trk.area = cv::countNonZero(trk.mask);
  double nx, ny;
  trk.center(nx, ny);
  const double mx = ((nx - ox) - trk.off_ego[0]) / dt, my = ((ny - oy) - trk.off_ego[1]) / dt;
  trk.off_ego[0] = trk.off_ego[1] = 0.0;
  const double a = cfg_.velocity_alpha;
  if (trk.hits == 1) {
    trk.vel[0] = mx;
    trk.vel[1] = my;
  } else {
    trk.vel[0] = a * mx + (1.0 - a) * trk.vel[0];
    trk.vel[1] = a * my + (1.0 - a) * trk.vel[1];
  }
  trk.hits += 1;
  trk.last_seen = f;
  trk.cls = det.cls;
  trk.role = det.role;
  if (trk.state == TrackState::Tentative && trk.hits >= cfg_.min_hits) trk.state = TrackState::Confirmed;
  else if (trk.state == TrackState::Lost) trk.state = TrackState::Confirmed;
  absorb_det(trk, det);
}

void MaskTracker::new_track(Instance &det) {
  Track trk;
  trk.id = next_id_;
  trk.cls = det.cls;
  trk.role = det.role;
  trk.box = det.bbox;
  trk.mask = det.crop().clone();
  trk.last_seen = frame_;
  trk.area = trk.mask.empty() ? 0 : cv::countNonZero(trk.mask);
  next_id_ += 1;
  if (cfg_.min_hits <= 1) trk.state = TrackState::Confirmed;
  tracks_.push_back(trk);
  absorb_det(tracks_.back(), det);
}

void MaskTracker::absorb_det(Track &trk, Instance &det) {
  det.track_id = trk.id;
  trk.still = det.status == Status::Still;
  if (std::isfinite(det.disparity)) {
    trk.disparity = det.disparity;
    trk.depth = det.depth;
    trk.sigma_z = det.sigma_z;
  }
  if (det.status == Status::Root || det.status == Status::Promoted) trk.last_promoted = frame_;
  else if (det.status == Status::Unpromoted && in_hysteresis(trk)) det.status = Status::Held;
}

std::optional<Instance> MaskTracker::carry(const Track &trk, int h, int w) const {
  int dx, dy;
  trk.shift(frame_, dx, dy);
  const Box b = shift_box(trk.box, dx, dy);
  const int cx0 = std::max(0, b.x0), cy0 = std::max(0, b.y0), cx1 = std::min(w, b.x1), cy1 = std::min(h, b.y1);
  if (cx1 <= cx0 || cy1 <= cy0) return std::nullopt;
  cv::Mat mask = cv::Mat::zeros(h, w, CV_8U);
  const cv::Rect dst(cx0, cy0, cx1 - cx0, cy1 - cy0), src(cx0 - b.x0, cy0 - b.y0, cx1 - cx0, cy1 - cy0);
  trk.mask(src).copyTo(mask(dst));
  if (cv::countNonZero(mask(dst)) == 0) return std::nullopt;
  const Box cb{cx0, cy0, cx1, cy1};
  Instance inst(mask, trk.cls, 0.0, &cb);
  inst.role = trk.role;
  inst.disparity = trk.disparity;
  inst.depth = trk.depth;
  inst.sigma_z = trk.sigma_z;
  inst.status = Status::Carried;
  inst.track_id = trk.id;
  return inst;
}

std::map<std::string, int> MaskTracker::summary() const {
  std::map<std::string, int> out = {{"tentative", 0}, {"confirmed", 0}, {"lost", 0}};
  for (const auto &t : tracks_) {
    if (t.state == TrackState::Tentative) out["tentative"]++;
    else if (t.state == TrackState::Confirmed) out["confirmed"]++;
    else if (t.state == TrackState::Lost) out["lost"]++;
  }
  return out;
}

}  // namespace savior
