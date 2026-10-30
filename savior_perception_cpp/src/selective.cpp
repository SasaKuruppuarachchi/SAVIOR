// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/selective.hpp"

#include <cmath>
#include <sstream>

namespace savior {

SelectivePolicy::SelectivePolicy(const SelectiveConfig &cfg, const MotionConfig &mcfg) : cfg_(cfg), mcfg_(mcfg) {
  std::stringstream ss(cfg.prior_static_classes);
  std::string tok;
  while (std::getline(ss, tok, ',')) {
    const std::string n = norm_name(tok);
    if (!n.empty()) prior_.insert(n);
  }
  reset();
}

void SelectivePolicy::reset() {
  mem_.clear();
  prev_t_.reset();
  onset_count_ = 0;
  onset_t_.reset();
  converged_ = false;
  stats_ = SelectiveStats();
}

std::string SelectivePolicy::revokes(const std::optional<InstFit> &ev, const std::optional<WinFit> &w,
                                     const std::optional<WinFit> &wl) const {
  const SelectiveConfig &c = cfg_;
  if (ev && ev->m2 >= c.revoke_q * c.revoke_q && ev->speed >= c.revoke_v_mps) return "i";
  const std::optional<WinFit> *ws[2] = {&w, &wl};
  const char *tags[2] = {"w", "l"};
  for (int k = 0; k < 2; ++k) {
    const auto &x = *ws[k];
    if (!x) continue;
    if (x->v_lat >= std::max(c.revoke_v_mps, c.revoke_q * x->s_lat)) return std::string(tags[k]) + "l";
    if (std::abs(x->v_rad) >= std::max(c.revoke_v_radial_mps, c.revoke_q * x->s_rad)) return std::string(tags[k]) + "r";
  }
  return "";
}

bool SelectivePolicy::static_bound(const std::optional<WinFit> &w) const {
  if (!w) return false;
  return w->v_lat + 2.0 * w->s_lat < mcfg_.v_static_mps &&
         (!mcfg_.radial_static_required || std::abs(w->v_rad) + 2.0 * w->s_rad < mcfg_.v_static_radial_mps);
}

std::string SelectivePolicy::observe(TrackMemory &mem, const MotionTrack::Raw *raw, double stamp) {
  const SelectiveConfig &c = cfg_;
  static const std::optional<InstFit> no_ev;
  static const std::optional<WinFit> no_win;
  const auto &ev = raw ? raw->ev : no_ev;
  const auto &win = raw ? raw->win : no_win;
  const auto &wl = raw ? raw->win_long : no_win;
  std::string obs;
  const std::string rv = revokes(ev, win, wl);
  if (!ev && !win && !wl) obs = "none";
  else if (!rv.empty()) {
    obs = "revoke";
    mem.revoke_by = rv;
  } else if ((!ev || ev->m2 < mcfg_.q_static * mcfg_.q_static) && (static_bound(win) || (c.long_static && static_bound(wl))))
    obs = "static";
  else
    obs = "uncertain";
  if (obs != "none") {
    const double hit = obs == "revoke" ? 1.0 : 0.0;
    if (!mem.ev_t0) {
      mem.ev_t0 = stamp;
      mem.rr = hit;
    } else {
      const double a = 1.0 - std::exp(-std::max(stamp - mem.ev_last_t, 0.0) / c.history_tau_s);
      mem.rr += a * (hit - mem.rr);
    }
    mem.ev_last_t = stamp;
  }
  if (obs == "revoke") {
    mem.run_t0.reset();
    mem.run_n = 0;
    mem.revoke_t = stamp;
  } else if (obs == "static" && stamp - mem.revoke_t >= c.revoke_hold_s) {
    if (!mem.run_t0) mem.run_t0 = stamp;
    mem.run_n += 1;
    mem.last_static_t = stamp;
  }
  if (mem.run_t0 && stamp - mem.last_static_t > c.stale_s) {
    mem.run_t0.reset();
    mem.run_n = 0;
  }
  mem.obs = obs;
  return obs;
}

bool SelectivePolicy::confirmed(const TrackMemory &mem, double stamp) const {
  const SelectiveConfig &c = cfg_;
  return mem.run_t0 && stamp - *mem.run_t0 >= c.confirm_s && mem.run_n >= c.confirm_min_obs &&
         stamp - mem.last_static_t <= c.stale_s;
}

bool SelectivePolicy::history_static(const TrackMemory &mem, double stamp) const {
  const SelectiveConfig &c = cfg_;
  return c.history_s > 0 && mem.ev_t0 && stamp - *mem.ev_t0 >= c.history_s && mem.rr < c.history_max_revoke &&
         stamp - mem.revoke_t >= std::min(c.revoke_hold_s, c.history_s);
}

void SelectivePolicy::update_convergence(double stamp, const MotionEstimator *motion) {
  const SelectiveConfig &c = cfg_;
  const EgoMotion *ego = (motion && motion->last_ego()) ? &*motion->last_ego() : nullptr;
  const double dt = prev_t_ ? stamp - *prev_t_ : 0.0;
  prev_t_ = stamp;
  if (!onset_t_) {
    if (ego && ego->t_ok && dt > 0 &&
        std::sqrt(ego->t[0] * ego->t[0] + ego->t[1] * ego->t[1] + ego->t[2] * ego->t[2]) / dt > c.onset_speed_mps) {
      onset_count_ += 1;
      if (onset_count_ >= c.onset_frames) onset_t_ = stamp;
    } else {
      onset_count_ = 0;
    }
  }
  converged_ = onset_t_ && stamp - *onset_t_ >= c.converge_s;
}

SelectiveContext SelectivePolicy::update(double stamp, std::vector<Instance> &instances, const MotionEstimator *motion) {
  update_convergence(stamp, motion);
  static const std::map<int, MotionTrack> empty;
  const std::map<int, MotionTrack> &tracks = motion ? motion->tracks() : empty;
  for (auto it = mem_.begin(); it != mem_.end();) {
    if (!tracks.count(it->first)) it = mem_.erase(it);
    else ++it;
  }
  SelectiveContext ctx;
  std::set<int> seen;
  int n_conf = 0;
  for (int i = 0; i < (int)instances.size(); ++i) {
    Instance &inst = instances[i];
    if (inst.role != Role::Potential) continue;
    const int tid = inst.motion ? inst.motion->id : -1;
    auto tt = inst.motion ? tracks.find(tid) : tracks.end();
    if (tt == tracks.end()) {
      ctx.labels[i] = "unknown";
      continue;
    }
    const MotionTrack &trk = tt->second;
    TrackMemory &mem = mem_[tid];
    const MotionTrack::Raw *raw = (trk.raw.valid && trk.raw.stamp == stamp) ? &trk.raw : nullptr;
    if (!seen.count(tid)) {
      seen.insert(tid);
      observe(mem, raw, stamp);
      mem.seen_t = stamp;
    }
    const bool conf = confirmed(mem, stamp);
    inst.win.reset();
    if (raw) {
      if (raw->win) inst.win = raw->win;
      else if (raw->win_long) inst.win = raw->win_long;
    }
    std::string lab;
    if (trk.is_moving) lab = "moving";
    else if (conf) {
      lab = "static";
      n_conf += 1;
    } else if (history_static(mem, stamp)) lab = "history";
    else lab = "unknown";
    ctx.labels[i] = lab;
    inst.motion->sel = lab;
    inst.motion->sel_obs = mem.obs + (mem.obs == "revoke" ? "_" + mem.revoke_by : std::string());
  }
  stats_ = SelectiveStats();
  stats_.converged = converged_;
  stats_.onset_t = onset_t_;
  stats_.n_static = n_conf;
  stats_.n_labels = (int)ctx.labels.size();
  for (auto &inst : instances) {
    if (inst.role != Role::Potential && inst.motion && tracks.count(inst.motion->id)) {
      const auto &raw = tracks.at(inst.motion->id).raw;
      if (raw.valid && raw.stamp == stamp) {
        if (raw.win) inst.win = raw.win;
        else if (raw.win_long) inst.win = raw.win_long;
        else inst.win.reset();
      }
    }
  }
  ctx.converged = converged_;
  ctx.prior = prior_;
  ctx.unknown_promotes = cfg_.unknown_promotes;
  ctx.comotion = cfg_.comotion_gate;
  ctx.comotion_q = cfg_.comotion_q;
  ctx.comotion_v_min = cfg_.comotion_v_min_mps;
  return ctx;
}

int SelectivePolicy::finalize(double stamp, std::vector<Instance> &instances) {
  int n_held = 0;
  const double hold = cfg_.min_on_s;
  for (auto &inst : instances) {
    if (inst.role != Role::Potential || !inst.motion) continue;
    auto it = mem_.find(inst.motion->id);
    if (it == mem_.end()) continue;
    TrackMemory &mem = it->second;
    if (inst.is_dynamic() && inst.status != Status::Held) mem.last_masked_t = stamp;
    else if (!inst.is_dynamic() && hold > 0 && stamp - mem.last_masked_t < hold) {
      inst.status = Status::Held;
      n_held += 1;
    }
  }
  stats_.n_held = n_held;
  return n_held;
}

}  // namespace savior
