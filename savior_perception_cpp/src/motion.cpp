// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/motion.py. Every step mirrors the Python implementation (same order of
// operations, same OpenCV calls with the same float32 conversions, Python dict orders reproduced) so the outputs agree
// up to floating-point summation order of the small linear-algebra kernels (numpy BLAS/einsum vs plain loops).
#include "savior_cpp/motion.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <set>

#include <opencv2/calib3d.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/video/tracking.hpp>

namespace savior {
namespace {

using Clock = std::chrono::steady_clock;
double ms_since(Clock::time_point a, Clock::time_point b) {
  return std::chrono::duration<double, std::milli>(b - a).count();
}

inline bool finite3(const Vec3 &v) { return std::isfinite(v[0]) && std::isfinite(v[1]) && std::isfinite(v[2]); }
inline double norm3(const Vec3 &v) { return std::sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]); }
inline Vec3 cross3(const Vec3 &a, const Vec3 &b) {  // np.cross component formulas
  return Vec3(a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]);
}
inline Vec3 unit3(const Vec3 &v) {
  const double n = std::max(norm3(v), 1e-12);
  return Vec3(v[0] / n, v[1] / n, v[2] / n);
}
inline Vec3 matvec(const Mat3 &R, const Vec3 &x) {  // (x @ R.T) row-vector convention == R x
  return Vec3(x[0] * R(0, 0) + x[1] * R(0, 1) + x[2] * R(0, 2), x[0] * R(1, 0) + x[1] * R(1, 1) + x[2] * R(1, 2),
              x[0] * R(2, 0) + x[1] * R(2, 1) + x[2] * R(2, 2));
}
inline Mat3 skew(const Vec3 &v) { return Mat3(0.0, -v[2], v[1], v[2], 0.0, -v[0], -v[1], v[0], 0.0); }
const Vec3 UP(0.0, 1.0, 0.0);

// 2x2 solve with partial pivoting (LAPACK dgesv order: pivot, multiply by reciprocal)
void solve2(double a00, double a01, double a10, double a11, double b0, double b1, double &x0, double &x1) {
  if (std::abs(a10) > std::abs(a00)) {
    std::swap(a00, a10);
    std::swap(a01, a11);
    std::swap(b0, b1);
  }
  const double l = a10 * (1.0 / a00);
  const double u11 = a11 - l * a01;
  const double y1 = b1 - l * b0;
  x1 = y1 / u11;
  x0 = (b0 - a01 * x1) / a00;
}

// small dense solve (Gaussian elimination with partial pivoting); returns false if singular
template <int N>
bool solveN(cv::Matx<double, N, N> A, cv::Vec<double, N> b, cv::Vec<double, N> &x) {
  for (int c = 0; c < N; ++c) {
    int p = c;
    for (int r = c + 1; r < N; ++r)
      if (std::abs(A(r, c)) > std::abs(A(p, c))) p = r;
    if (A(p, c) == 0.0) return false;
    if (p != c) {
      for (int k = 0; k < N; ++k) std::swap(A(p, k), A(c, k));
      std::swap(b[p], b[c]);
    }
    const double inv = 1.0 / A(c, c);
    for (int r = c + 1; r < N; ++r) {
      const double l = A(r, c) * inv;
      A(r, c) = l;
      for (int k = c + 1; k < N; ++k) A(r, k) -= l * A(c, k);
      b[r] -= l * b[c];
    }
  }
  for (int r = N - 1; r >= 0; --r) {
    double s = b[r];
    for (int k = r + 1; k < N; ++k) s -= A(r, k) * x[k];
    x[r] = s / A(r, r);
  }
  return true;
}

}  // namespace

// ------------------------------------------------------------------------------------------------ SO(3)
Mat3 so3_exp(const Vec3 &w) {
  const double th = norm3(w);
  const Mat3 K = skew(w);
  if (th < 1e-9) return Mat3::eye() + K;
  return Mat3::eye() + (std::sin(th) / th) * K + ((1.0 - std::cos(th)) / (th * th)) * (K * K);
}

Vec3 so3_log(const Mat3 &R) {
  const double c = std::max(-1.0, std::min(1.0, (R(0, 0) + R(1, 1) + R(2, 2) - 1.0) * 0.5));
  const double th = std::acos(c);
  const Vec3 v(R(2, 1) - R(1, 2), R(0, 2) - R(2, 0), R(1, 0) - R(0, 1));
  if (th < 1e-7) return 0.5 * v;
  return (th / (2.0 * std::sin(th))) * v;
}

// ------------------------------------------------------------------------------------------------ gyro
void GyroIntegrator::add(double t, const Vec3 &w) {
  if (!t_.empty() && t <= t_.back()) {
    if (t == t_.back()) return;
    auto it = std::lower_bound(t_.begin(), t_.end(), t);
    if (it != t_.end() && *it == t) return;
    const size_t i = it - t_.begin();
    t_.insert(it, t);
    w_.insert(w_.begin() + i, w);
    return;
  }
  t_.push_back(t);
  w_.push_back(w);
  if (t_.back() - t_.front() > 2 * max_age_s_) {
    const size_t k = std::lower_bound(t_.begin(), t_.end(), t_.back() - max_age_s_) - t_.begin();
    t_.erase(t_.begin(), t_.begin() + k);
    w_.erase(w_.begin(), w_.begin() + k);
  }
}

Vec3 GyroIntegrator::omega(double t) const {
  const size_t i = std::lower_bound(t_.begin(), t_.end(), t) - t_.begin();
  if (i == 0) return w_.front();
  if (i >= t_.size()) return w_.back();
  const double t0 = t_[i - 1], t1 = t_[i];
  const double a = t1 > t0 ? (t - t0) / (t1 - t0) : 0.0;
  return (1.0 - a) * w_[i - 1] + a * w_[i];
}

std::optional<Mat3> GyroIntegrator::rotation(double t0, double t1) const {
  if (t1 < t0) {
    auto R = rotation(t1, t0);
    if (!R) return std::nullopt;
    return R->t();
  }
  if (!covers(t0, t1)) return std::nullopt;
  const size_t i0 = std::upper_bound(t_.begin(), t_.end(), t0) - t_.begin();
  const size_t i1 = std::lower_bound(t_.begin(), t_.end(), t1) - t_.begin();
  std::vector<double> knots;
  knots.push_back(t0);
  for (size_t i = i0; i < i1; ++i) knots.push_back(t_[i]);
  knots.push_back(t1);
  Mat3 R = Mat3::eye();
  Vec3 w_prev = omega(t0);
  for (size_t k = 0; k + 1 < knots.size(); ++k) {
    const double a = knots[k], b = knots[k + 1];
    const Vec3 w_b = omega(b);
    if (b > a) R = R * so3_exp((0.5 * (w_prev + w_b)) * (b - a));
    w_prev = w_b;
  }
  return R;
}

// ------------------------------------------------------------------------------------------------ estimator
MotionEstimator::MotionEstimator(const MotionConfig &cfg, const StereoRectifier &rect, const cv::Mat &static_mask)
    : cfg_(cfg), rect_(rect) {
  const CameraModel &c0 = rect.cams[0];
  f_raw_ = (c0.K(0, 0) + c0.K(1, 1)) / 2.0;
  const Mat4 Tinv = c0.T_cam_imu.inv(cv::DECOMP_LU);
  for (int r = 0; r < 3; ++r)
    for (int k = 0; k < 3; ++k) R_CI_(r, k) = Tinv(r, k);
  s_ = cfg.image_scale;
  size_s_w_ = std::max(8, (int)std::nearbyint(c0.width * s_));
  size_s_h_ = std::max(8, (int)std::nearbyint(c0.height * s_));
  if (!static_mask.empty()) {
    cv::Mat m = static_mask > 127;  // 0/255
    m = m / 255;
    cv::resize(m, static_mask_s_, cv::Size(size_s_w_, size_s_h_), 0, 0, cv::INTER_NEAREST);
  }
  win_ = cv::Size((int)cfg.klt_win, (int)cfg.klt_win);
  crit_ = cv::TermCriteria(cv::TermCriteria::COUNT | cv::TermCriteria::EPS, 20, 0.03);
  reset();
}

void MotionEstimator::reset() {
  prev_pyr_ = cv::Mat();
  prev_t_.reset();
  bg_p_.clear();
  bg_X_.clear();
  bg_age_.clear();
  in_p_.clear();
  in_X_.clear();
  in_tid_.clear();
  tracks_.clear();
  next_id_ = 1;
  last_ego_.reset();
  stats_ = MotionStats();
  poses_.clear();
  frame_ = 0;
}

void MotionEstimator::bearings(const std::vector<cv::Point2d> &pts, int cam, std::vector<Vec3> &b,
                               std::vector<uint8_t> &ok) const {
  const size_t n = pts.size();
  b.assign(n, Vec3(0, 0, 0));
  ok.assign(n, 0);
  if (!n) return;
  const CameraModel &c = rect_.cams[cam];
  cv::Mat src(n, 1, CV_64FC2, (void *)pts.data()), dst;
  if (c.is_fisheye())
    cv::fisheye::undistortPoints(src, dst, cv::Mat(c.K), cv::Mat(c.D));
  else
    cv::undistortPoints(src, dst, cv::Mat(c.K), cv::Mat(c.D), cv::noArray(), cv::noArray(),
                        cv::TermCriteria(cv::TermCriteria::COUNT | cv::TermCriteria::EPS, 20, 1e-9));
  for (size_t i = 0; i < n; ++i) {
    const double *p = dst.ptr<double>((int)i);
    double x = p[0], y = p[1];
    const bool o = std::isfinite(x) && std::isfinite(y) && std::abs(x) < 20 && std::abs(y) < 20;
    ok[i] = o;
    if (!o) x = y = 0.0;
    b[i] = unit3(Vec3(x, y, 1.0));
  }
}

void MotionEstimator::rect_uv(const std::vector<Vec3> &b, int cam, std::vector<cv::Point2d> &uv,
                              std::vector<uint8_t> &ok) const {
  uv.resize(b.size());
  ok.resize(b.size());
  for (size_t i = 0; i < b.size(); ++i) {
    const Vec3 r = matvec(rect_.R_rect[cam], b[i]);
    ok[i] = r[2] > 1e-6;
    const double z = ok[i] ? r[2] : 1.0;
    uv[i] = cv::Point2d(rect_.f * r[0] / z + rect_.cx, rect_.f * r[1] / z + rect_.cy);
  }
}

Vec3 MotionEstimator::point_from_disparity(const Vec3 &b, double d) const {
  const Vec3 r = matvec(rect_.R_rect[0], b);
  const double z = d > 0 ? rect_.fb() / d : NaN;
  const double lam = z / r[2];
  return Vec3(b[0] * lam, b[1] * lam, b[2] * lam);
}

bool MotionEstimator::ego_project(const std::vector<cv::Point2d> &pts, const std::vector<double> &depth,
                                  std::vector<cv::Point2d> &out) const {
  if (!last_ego_ || pts.empty()) return false;
  const EgoMotion &ego = *last_ego_;
  std::vector<Vec3> b;
  std::vector<uint8_t> ok;
  bearings(pts, 0, b, ok);
  std::vector<cv::Point3d> Yp(pts.size());
  std::vector<uint8_t> front(pts.size());
  for (size_t i = 0; i < pts.size(); ++i) {
    const Vec3 r = matvec(rect_.R_rect[0], b[i]);
    const double z = (std::isfinite(depth[i]) && depth[i] > 0) ? depth[i] : 1e6;
    const double lam = z / std::max(r[2], 1e-6);
    const Vec3 X(b[i][0] * lam, b[i][1] * lam, b[i][2] * lam);
    const Vec3 Y = matvec(ego.R, X) + ego.t;
    front[i] = Y[2] > 1e-6;
    Yp[i] = front[i] ? cv::Point3d(Y[0], Y[1], Y[2]) : cv::Point3d(0, 0, 1.0);
  }
  out = rect_.cams[0].project(Yp);
  for (size_t i = 0; i < pts.size(); ++i)
    if (!ok[i] || !front[i]) out[i] = cv::Point2d(NaN, NaN);
  return true;
}

cv::Mat MotionEstimator::pyr(const cv::Mat &gray) const {
  if (s_ == 1.0) return gray;
  cv::Mat o;
  cv::resize(gray, o, cv::Size(size_s_w_, size_s_h_), 0, 0, cv::INTER_AREA);
  return o;
}

void MotionEstimator::fb_ok(const cv::Mat &img0, const cv::Mat &img1, const std::vector<cv::Point2d> &p0,
                            const std::vector<cv::Point2d> &p1, const std::vector<uint8_t> &ok,
                            std::vector<uint8_t> &res) const {
  res.assign(p0.size(), 0);
  std::vector<size_t> idx;
  for (size_t i = 0; i < ok.size(); ++i)
    if (ok[i]) idx.push_back(i);
  if (idx.empty()) return;
  std::vector<cv::Point2f> a(idx.size()), b0(idx.size()), pb;
  for (size_t k = 0; k < idx.size(); ++k) {
    a[k] = cv::Point2f((float)(p1[idx[k]].x * s_), (float)(p1[idx[k]].y * s_));
    b0[k] = cv::Point2f((float)(p0[idx[k]].x * s_), (float)(p0[idx[k]].y * s_));
  }
  pb = b0;
  std::vector<uchar> st;
  std::vector<float> err;
  cv::calcOpticalFlowPyrLK(img1, img0, a, pb, st, err, win_, (int)cfg_.klt_levels, crit_, cv::OPTFLOW_USE_INITIAL_FLOW);
  const float sf = (float)s_, fbm = (float)cfg_.fb_max_px;
  for (size_t k = 0; k < idx.size(); ++k) {
    const float dx = pb[k].x - b0[k].x, dy = pb[k].y - b0[k].y;
    const float e = std::sqrt(dx * dx + dy * dy) / sf;
    res[idx[k]] = st[k] && e < fbm;
  }
}

void MotionEstimator::klt(const cv::Mat &img0, const cv::Mat &img1, const std::vector<cv::Point2d> &pts, bool fb,
                          std::vector<cv::Point2d> &out, std::vector<uint8_t> &ok) const {
  out.clear();
  ok.clear();
  if (pts.empty()) return;
  std::vector<cv::Point2f> p0(pts.size()), p1;
  for (size_t i = 0; i < pts.size(); ++i) p0[i] = cv::Point2f((float)(pts[i].x * s_), (float)(pts[i].y * s_));
  std::vector<uchar> st;
  std::vector<float> err;
  cv::calcOpticalFlowPyrLK(img0, img1, p0, p1, st, err, win_, (int)cfg_.klt_levels, crit_, 0);
  ok.resize(pts.size());
  for (size_t i = 0; i < pts.size(); ++i) ok[i] = st[i] != 0;
  if (fb) {
    std::vector<cv::Point2f> p0b = p0;
    std::vector<uchar> st2;
    cv::calcOpticalFlowPyrLK(img1, img0, p1, p0b, st2, err, win_, (int)cfg_.klt_levels, crit_,
                             cv::OPTFLOW_USE_INITIAL_FLOW);
    const float sf = (float)s_, fbm = (float)cfg_.fb_max_px;
    for (size_t i = 0; i < pts.size(); ++i) {
      const float dx = p0b[i].x - p0[i].x, dy = p0b[i].y - p0[i].y;
      ok[i] = ok[i] && st2[i] && (std::sqrt(dx * dx + dy * dy) / sf < fbm);
    }
  }
  out.resize(pts.size());
  const int w = rect_.cams[0].width, h = rect_.cams[0].height;
  for (size_t i = 0; i < pts.size(); ++i) {
    out[i] = cv::Point2d((double)p1[i].x / s_, (double)p1[i].y / s_);
    ok[i] = ok[i] && out[i].x >= 0 && out[i].x <= w - 1 && out[i].y >= 0 && out[i].y <= h - 1;
  }
}

// ------------------------------------------------------------------------------------------------ ego-motion
EgoMotion MotionEstimator::estimate_ego(const std::vector<Vec3> &X, const std::vector<Vec3> &b, const Mat3 &R_g,
                                        double dt, double gyro_sigma) const {
  const MotionConfig &c = cfg_;
  const double sig_min = c.sigma_px_min / f_raw_;
  const double st0 = std::max(c.max_ego_speed_mps * std::max(dt, 1e-3), 1e-3);
  const size_t n = X.size();
  EgoMotion ego;
  ego.R = R_g;
  ego.t = Vec3(0, 0, 0);
  ego.sigma_t = st0;
  ego.sigma_bg = 2.0 * sig_min;
  ego.n_bg = (int)n;
  if ((long)n < std::max<long>(6, c.bg_min_inliers / 2)) return ego;
  std::vector<Vec3> Xr(n);
  for (size_t i = 0; i < n; ++i) Xr[i] = matvec(R_g, X[i]);
  cv::Vec<double, 6> x = cv::Vec<double, 6>::all(0.0);
  double sigma = 2.0 * sig_min;
  std::vector<double> w_rob(n, 1.0), rn(n);
  const double gs = gyro_sigma;
  cv::Matx<double, 6, 6> prior = cv::Matx<double, 6, 6>::zeros();
  for (int k = 0; k < 3; ++k) prior(k, k) = 1.0 / (gs * gs);
  for (int k = 3; k < 6; ++k) prior(k, k) = 1.0 / (st0 * st0);
  cv::Matx<double, 6, 6> H = prior;
  std::vector<Vec3> Yp(n), res(n);
  std::vector<double> nY(n);
  for (int it = 0; it < (int)c.ego_iters; ++it) {
    const Mat3 Rc = so3_exp(Vec3(x[0], x[1], x[2]));
    for (size_t i = 0; i < n; ++i) {
      Yp[i] = matvec(Rc, Xr[i]);
      const Vec3 Y(Yp[i][0] + x[3], Yp[i][1] + x[4], Yp[i][2] + x[5]);
      nY[i] = norm3(Y);
      const Vec3 u(Y[0] / nY[i], Y[1] / nY[i], Y[2] / nY[i]);
      res[i] = cross3(b[i], u);
      rn[i] = norm3(res[i]);
    }
    if (it >= 1) {
      std::vector<double> sel;
      for (size_t i = 0; i < n; ++i)
        if (w_rob[i] > 0) sel.push_back(rn[i]);
      const double med = sel.empty() ? sigma : median_f64(sel);
      sigma = std::max(sig_min, med / 1.1774);
    }
    const double k = 2.0 * sigma;
    for (size_t i = 0; i < n; ++i) {
      w_rob[i] = rn[i] <= k ? 1.0 : k / std::max(rn[i], 1e-15);
      if (it >= 2 && rn[i] > 4.0 * sigma) w_rob[i] = 0.0;
    }
    cv::Matx<double, 6, 6> A = cv::Matx<double, 6, 6>::zeros();
    cv::Vec<double, 6> g = cv::Vec<double, 6>::all(0.0);
    const double s2 = sigma * sigma;
    for (size_t i = 0; i < n; ++i) {
      // J_i = [b]x [-[Yp]x, I] / |Y| ; [b]x[Yp]x = Yp b^T - (b.Yp) I
      const Vec3 &bb = b[i], &yp = Yp[i];
      const double bp = bb[0] * yp[0] + bb[1] * yp[1] + bb[2] * yp[2];
      double J[3][6];
      for (int r = 0; r < 3; ++r)
        for (int q = 0; q < 3; ++q) {
          double BP = yp[r] * bb[q];
          if (r == q) BP -= bp;
          J[r][q] = -BP / nY[i];
        }
      const double Bx[3][3] = {{0.0, -bb[2], bb[1]}, {bb[2], 0.0, -bb[0]}, {-bb[1], bb[0], 0.0}};
      for (int r = 0; r < 3; ++r)
        for (int q = 0; q < 3; ++q) J[r][3 + q] = Bx[r][q] / nY[i];
      const double W = w_rob[i] / s2;
      for (int r = 0; r < 3; ++r)
        for (int j = 0; j < 6; ++j) {
          const double jw = J[r][j] * W;
          for (int q = 0; q < 6; ++q) A(j, q) += jw * J[r][q];
          g[j] += jw * res[i][r];
        }
    }
    H = prior + A;
    cv::Vec<double, 6> px = prior * x;
    for (int j = 0; j < 6; ++j) g[j] += px[j];
    cv::Vec<double, 6> dx;
    if (!solveN<6>(H, g, dx)) return ego;
    for (int j = 0; j < 6; ++j) x[j] -= dx[j];
    double nd = 0;
    for (int j = 0; j < 6; ++j) nd += dx[j] * dx[j];
    if (it >= 2 && std::sqrt(nd) < 1e-7) break;
  }
  const Mat3 Rc = so3_exp(Vec3(x[0], x[1], x[2]));
  int inl = 0;
  for (size_t i = 0; i < n; ++i) {
    const Vec3 Yr = matvec(Rc, Xr[i]);
    const Vec3 Y(Yr[0] + x[3], Yr[1] + x[4], Yr[2] + x[5]);
    if (norm3(cross3(b[i], unit3(Y))) < 3.0 * sigma) ++inl;
  }
  ego.n_inliers = inl;
  ego.dtheta = Vec3(x[0], x[1], x[2]);
  ego.R = Rc * R_g;
  ego.sigma_bg = sigma;
  if (ego.n_inliers >= c.bg_min_inliers) {
    cv::Matx<double, 6, 6> cov;
    if (cv::invert(H, cov, cv::DECOMP_LU) != 0) {
      double m = cov(3, 3);
      for (int k = 4; k < 6; ++k) m = std::max(m, cov(k, k));
      ego.sigma_t = std::sqrt(std::max(m, 0.0));
    } else {
      ego.sigma_t = st0;
    }
    ego.t = Vec3(x[3], x[4], x[5]);
    ego.t_ok = true;
  } else {
    ego.R = R_g;
    ego.dtheta = Vec3(0, 0, 0);
  }
  return ego;
}

// ------------------------------------------------------------------------------------------------ instantaneous test
std::map<int, InstFit> MotionEstimator::instance_fits(const std::vector<Group> &groups, const EgoMotion &ego,
                                                      double dt) const {
  const MotionConfig &c = cfg_;
  std::vector<int> keys;
  std::vector<Vec3> Y, b;
  std::vector<int> g;
  for (const auto &grp : groups) {
    if ((long)grp.X.size() < c.min_points) continue;
    const int gi = (int)keys.size();
    keys.push_back(grp.key);
    for (size_t i = 0; i < grp.X.size(); ++i) {
      const Vec3 y = matvec(ego.R, grp.X[i]) + ego.t;
      if (!(y[2] > 1e-3)) continue;
      Y.push_back(y);
      b.push_back(grp.b[i]);
      g.push_back(gi);
    }
  }
  std::map<int, InstFit> out;
  if (keys.empty()) return out;
  const int G = (int)keys.size();
  std::vector<int> cnt(G, 0);
  for (int gi : g) cnt[gi]++;
  bool any_good = false;
  for (int j = 0; j < G; ++j) any_good |= cnt[j] >= c.min_points;
  if (!any_good) return out;
  {
    std::vector<Vec3> Y2, b2;
    std::vector<int> g2;
    for (size_t i = 0; i < g.size(); ++i)
      if (cnt[g[i]] >= c.min_points) {
        Y2.push_back(Y[i]);
        b2.push_back(b[i]);
        g2.push_back(g[i]);
      }
    Y.swap(Y2);
    b.swap(b2);
    g.swap(g2);
  }
  const size_t n = g.size();
  std::vector<double> rngs(n);
  std::vector<Vec3> y(n);
  std::vector<Vec3> msum(G, Vec3(0, 0, 0));
  for (size_t i = 0; i < n; ++i) {
    rngs[i] = norm3(Y[i]);
    y[i] = Vec3(Y[i][0] / rngs[i], Y[i][1] / rngs[i], Y[i][2] / rngs[i]);
    for (int k = 0; k < 3; ++k) msum[g[i]][k] += y[i][k];
  }
  std::vector<Vec3> ug(G), vg(G);
  for (int j = 0; j < G; ++j) {
    const Vec3 mg = unit3(Vec3(msum[j][0] + 1e-12, msum[j][1] + 1e-12, msum[j][2] + 1e-12));
    Vec3 u = cross3(mg, UP);
    if (norm3(u) < 1e-6) u = cross3(mg, Vec3(1.0, 0.0, 0.0));
    ug[j] = unit3(u);
    vg[j] = cross3(mg, ug[j]);
  }
  std::vector<double> e0(n), e1(n), w00(n), w11(n), w01(n);
  const double s2 = ego.sigma_bg * ego.sigma_bg;
  const double dr2 = c.depth_rel_sigma * c.depth_rel_sigma;
  const Vec3 &t = ego.t;
  for (size_t i = 0; i < n; ++i) {
    const Vec3 &u = ug[g[i]], &v = vg[g[i]];
    const Vec3 d(b[i][0] - y[i][0], b[i][1] - y[i][1], b[i][2] - y[i][2]);
    e0[i] = d[0] * u[0] + d[1] * u[1] + d[2] * u[2];
    e1[i] = d[0] * v[0] + d[1] * v[1] + d[2] * v[2];
    const double yt = y[i][0] * t[0] + y[i][1] * t[1] + y[i][2] * t[2];
    const Vec3 par((t[0] - yt * y[i][0]) / rngs[i], (t[1] - yt * y[i][1]) / rngs[i], (t[2] - yt * y[i][2]) / rngs[i]);
    const double px = par[0] * u[0] + par[1] * u[1] + par[2] * u[2];
    const double py = par[0] * v[0] + par[1] * v[1] + par[2] * v[2];
    const double det = s2 * s2 + s2 * dr2 * (px * px + py * py);
    w00[i] = (s2 + dr2 * py * py) / det;
    w11[i] = (s2 + dr2 * px * px) / det;
    w01[i] = -dr2 * px * py / det;
  }
  std::vector<double> wr(n, 1.0), md2(n);
  std::vector<double> a00(G), a11(G), a01(G), cx(G), cy(G);
  for (int it = 0; it < 4; ++it) {
    std::vector<double> r0(G, 0.0), r1(G, 0.0);
    std::fill(a00.begin(), a00.end(), 0.0);
    std::fill(a11.begin(), a11.end(), 0.0);
    std::fill(a01.begin(), a01.end(), 0.0);
    for (size_t i = 0; i < n; ++i) {
      const int j = g[i];
      a00[j] += wr[i] * w00[i];
      a11[j] += wr[i] * w11[i];
      a01[j] += wr[i] * w01[i];
      r0[j] += wr[i] * (w00[i] * e0[i] + w01[i] * e1[i]);
      r1[j] += wr[i] * (w01[i] * e0[i] + w11[i] * e1[i]);
    }
    for (int j = 0; j < G; ++j) {
      double dh = a00[j] * a11[j] - a01[j] * a01[j];
      if (!(std::abs(dh) > 0)) dh = 1e-30;
      cx[j] = (a11[j] * r0[j] - a01[j] * r1[j]) / dh;
      cy[j] = (a00[j] * r1[j] - a01[j] * r0[j]) / dh;
    }
    for (size_t i = 0; i < n; ++i) {
      const double q0 = e0[i] - cx[g[i]], q1 = e1[i] - cy[g[i]];
      md2[i] = w00[i] * q0 * q0 + 2 * w01[i] * q0 * q1 + w11[i] * q1 * q1;
      if (it < 3) {
        const double md = std::sqrt(md2[i]);
        wr[i] = md <= 2.0 ? 1.0 : 2.0 / std::max(md, 1e-12);
      }
    }
  }
  std::vector<double> chi2(G, 0.0), covt(G, 0.0);
  std::vector<int> n_g(G, 0);
  for (size_t i = 0; i < n; ++i) {
    chi2[g[i]] += wr[i] * md2[i];
    n_g[g[i]]++;
    const double st = ego.sigma_t / rngs[i];
    covt[g[i]] += st * st;
  }
  const double dtc = std::max(dt, 1e-3);
  const double sys = c.sigma_sys_px / f_raw_;
  for (int j = 0; j < G; ++j) {
    if (n_g[j] < c.min_points) continue;
    const double scale = std::max(1.0, chi2[j] / std::max(1, 2 * n_g[j] - 2));
    const double coh = sys * sys + covt[j] / std::max(n_g[j], 1);
    std::vector<double> rr;
    for (size_t i = 0; i < n; ++i)
      if (g[i] == j) rr.push_back(rngs[i]);
    const double rng = median_f64(rr);
    const double dh = a00[j] * a11[j] - a01[j] * a01[j];
    const double c00 = a11[j] / dh * scale + coh, c01 = -a01[j] / dh * scale, c11 = a00[j] / dh * scale + coh;
    double s0, s1;
    solve2(c00, c01, c01, c11, cx[j], cy[j], s0, s1);
    InstFit f;
    f.n = n_g[j];
    f.rng = rng;
    f.m2 = cx[j] * s0 + cy[j] * s1;
    const double k = rng / dtc;
    for (int q = 0; q < 3; ++q) f.v[q] = (cx[j] * ug[j][q] + cy[j] * vg[j][q]) * k;
    f.speed = std::hypot(cx[j], cy[j]) * k;
    f.cov[0] = c00 * k * k;
    f.cov[1] = c01 * k * k;
    f.cov[2] = c01 * k * k;
    f.cov[3] = c11 * k * k;
    out[keys[j]] = f;
  }
  return out;
}

std::vector<std::optional<Vec3>> MotionEstimator::anchor_points(const std::vector<const Instance *> &insts) const {
  std::vector<std::optional<Vec3>> out(insts.size());
  std::vector<size_t> idx;
  std::vector<cv::Point2d> cpts;
  for (size_t k = 0; k < insts.size(); ++k) {
    const Instance &inst = *insts[k];
    if (!(std::isfinite(inst.depth) && inst.depth > 0)) continue;
    const cv::Moments mom = cv::moments(inst.crop(), true);
    if (mom.m00 <= 0) continue;
    idx.push_back(k);
    cpts.emplace_back(inst.bbox.x0 + mom.m10 / mom.m00, inst.bbox.y0 + mom.m01 / mom.m00);
  }
  if (idx.empty()) return out;
  std::vector<Vec3> b;
  std::vector<uint8_t> ok;
  bearings(cpts, 0, b, ok);
  const Mat3 &R0 = rect_.R_rect[0];
  for (size_t j = 0; j < idx.size(); ++j) {
    const double rz = b[j][0] * R0(2, 0) + b[j][1] * R0(2, 1) + b[j][2] * R0(2, 2);
    if (ok[j] && rz > 1e-3) {
      const double lam = insts[idx[j]]->depth / rz;
      out[idx[j]] = Vec3(b[j][0] * lam, b[j][1] * lam, b[j][2] * lam);
    }
  }
  return out;
}

std::optional<WinFit> MotionEstimator::window_fit(const MotionTrack &trk, double stamp, double wmin, double wmax) const {
  (void)stamp;
  const MotionConfig &c = cfg_;
  if (trk.hist.empty()) return std::nullopt;
  const auto &hk = trk.hist.back();
  const MotionTrack::Hist *hj = nullptr;
  for (size_t i = 0; i + 1 < trk.hist.size(); ++i) {
    const auto &h = trk.hist[i];
    const double d = hk.stamp - h.stamp;
    if (wmin <= d && d <= wmax && poses_.count(h.frame)) {
      hj = &h;
      break;
    }
  }
  if (!hj || !poses_.count(hk.frame)) return std::nullopt;
  const Mat4 T = poses_.at(hk.frame).inv(cv::DECOMP_LU) * poses_.at(hj->frame);
  Vec3 Pj_k;
  for (int r = 0; r < 3; ++r) Pj_k[r] = T(r, 0) * hj->P[0] + T(r, 1) * hj->P[1] + T(r, 2) * hj->P[2] + T(r, 3);
  const Vec3 &Pk = hk.P;
  const Vec3 D = Pk - Pj_k;
  const double r = norm3(Pk);
  const Vec3 ur(Pk[0] / r, Pk[1] / r, Pk[2] / r);
  const double dtw = hk.stamp - hj->stamp;
  const double Dr = D[0] * ur[0] + D[1] * ur[1] + D[2] * ur[2];
  WinFit w;
  w.v_rad = Dr / dtw;
  const Vec3 L(D[0] - Dr * ur[0], D[1] - Dr * ur[1], D[2] - Dr * ur[2]);
  w.v_lat = norm3(L) / dtw;
  const double z = Pk[2];
  w.s_rad = std::sqrt(2.0) * r * (z * c.anchor_sigma_d_px / rect_.fb()) / dtw;
  w.s_lat = std::sqrt(2.0) * r * (c.anchor_sigma_px / f_raw_) / dtw;
  w.dt = dtw;
  for (int q = 0; q < 3; ++q) {
    w.V[q] = D[q] / dtw;
    w.ur[q] = ur[q];
  }
  return w;
}

void MotionEstimator::observe(MotionTrack &trk, const std::optional<InstFit> &ev, const std::optional<WinFit> &win) const {
  const MotionConfig &c = cfg_;
  if (!ev && !win) {
    trk.last = MotionInfo();
    trk.last.obs = "none";
    return;
  }
  bool moving = false, inst_static = true;
  if (ev) {
    moving = ev->m2 >= c.q_move * c.q_move && ev->speed >= c.v_move_mps;
    inst_static = ev->m2 < c.q_static * c.q_static;
  }
  if (win && (trk.role == Role::Dynamic || c.window_moving_potential))
    moving = moving || (win->v_lat >= std::max(c.v_move_mps, c.q_move * win->s_lat) ||
                        std::abs(win->v_rad) >= std::max(c.v_move_radial_mps, c.q_move * win->s_rad));
  bool contra = false;
  if (win && !moving && trk.role != Role::Dynamic && c.window_unveto_potential && !c.window_moving_potential)
    contra = (win->v_lat >= std::max(c.v_move_mps, c.q_move * win->s_lat) ||
              std::abs(win->v_rad) >= std::max(c.v_move_radial_mps, c.q_move * win->s_rad));
  const bool stat = (!moving && !contra && inst_static && win && win->v_lat + 2.0 * win->s_lat < c.v_static_mps &&
                     (!c.radial_static_required || std::abs(win->v_rad) + 2.0 * win->s_rad < c.v_static_radial_mps));
  trk.n_obs += 1;
  if (moving) trk.l = std::min(c.l_max, trk.l + c.l_up);
  else if (stat) trk.l = std::max(-c.l_max, trk.l - c.l_down);
  else if (contra) trk.l = std::max(trk.l, 0.0);
  if (trk.l >= c.th_moving) trk.is_moving = true;
  else if (trk.l <= 0.0) trk.is_moving = false;
  if (trk.l <= c.th_static) trk.is_static = true;
  else if (trk.l >= 0.0) trk.is_static = false;
  MotionInfo out;
  out.obs = moving ? "moving" : (stat ? "static" : (contra ? "contra" : "uncertain"));
  if (ev) {
    out.has_ev = true;
    out.speed = round_ndigits(ev->speed, 3);
    out.q = round_ndigits(std::sqrt(ev->m2), 2);
    out.n = ev->n;
    out.rng = round_ndigits(ev->rng, 2);
  }
  if (win) {
    out.has_win = true;
    out.w_lat = round_ndigits(win->v_lat, 3);
    out.w_slat = round_ndigits(win->s_lat, 3);
    out.w_rad = round_ndigits(win->v_rad, 3);
    out.w_srad = round_ndigits(win->s_rad, 3);
  }
  trk.last = out;
}

// ------------------------------------------------------------------------------------------------ point management
std::vector<cv::Point2d> MotionEstimator::detect_in_instance(const cv::Mat &img_s, const Instance &inst, int n, int er,
                                                             const std::vector<cv::Point2d> &existing) const {
  const double s = s_;
  const Box &bb = inst.bbox;
  const int sx0 = (int)std::floor(bb.x0 * s), sy0 = (int)std::floor(bb.y0 * s);
  const int sx1 = std::min(size_s_w_, (int)std::ceil(bb.x1 * s)), sy1 = std::min(size_s_h_, (int)std::ceil(bb.y1 * s));
  if (sx1 - sx0 < 4 || sy1 - sy0 < 4) return {};
  cv::Mat m;
  cv::resize(inst.crop(), m, cv::Size(sx1 - sx0, sy1 - sy0), 0, 0, cv::INTER_NEAREST);
  if (er > 0) cv::erode(m, m, cv::Mat::ones(2 * er + 1, 2 * er + 1, CV_8U));
  for (const auto &p : existing)
    cv::circle(m, cv::Point((int)(p.x * s) - sx0, (int)(p.y * s) - sy0), 3, cv::Scalar(0), -1);
  if (!static_mask_s_.empty()) {
    cv::Mat sm = static_mask_s_(cv::Rect(sx0, sy0, sx1 - sx0, sy1 - sy0));
    m.setTo(0, sm);
  }
  if (cv::countNonZero(m) == 0) return {};
  std::vector<cv::Point2f> c;
  // numpy view -> OpenCV without the parent image: the corner filters must see the crop border (clone)
  cv::goodFeaturesToTrack(img_s(cv::Rect(sx0, sy0, sx1 - sx0, sy1 - sy0)).clone(), c, n, 0.01, 3, m * 255, 5);
  std::vector<cv::Point2d> out;
  for (const auto &p : c) out.emplace_back(((double)p.x + sx0) / s, ((double)p.y + sy0) / s);
  return out;
}

std::vector<cv::Point2d> MotionEstimator::detect_background(const cv::Mat &img_s, const std::vector<Box> &boxes,
                                                            const std::vector<cv::Point2d> &existing, int n) const {
  if (n <= 0) return {};
  const double s = s_;
  cv::Mat m(img_s.size(), CV_8U, cv::Scalar(255));
  if (!static_mask_s_.empty()) m.setTo(0, static_mask_s_);
  for (const auto &b : boxes) {
    int ya = (int)(b.y0 * s), yb = std::min(m.rows, (int)std::ceil(b.y1 * s));
    int xa = (int)(b.x0 * s), xb = std::min(m.cols, (int)std::ceil(b.x1 * s));
    ya = std::min(ya, m.rows);
    xa = std::min(xa, m.cols);
    if (yb > ya && xb > xa) m(cv::Rect(xa, ya, xb - xa, yb - ya)).setTo(0);
  }
  for (const auto &p : existing) cv::circle(m, cv::Point((int)(p.x * s), (int)(p.y * s)), 8, cv::Scalar(0), -1);
  std::vector<cv::Point2f> c;
  cv::goodFeaturesToTrack(img_s, c, n, 0.01, 8, m, 5);
  std::vector<cv::Point2d> out;
  for (const auto &p : c) out.emplace_back((double)p.x / s, (double)p.y / s);
  return out;
}

void MotionEstimator::stereo_disp(const cv::Mat &img_l, const cv::Mat *right, const std::vector<cv::Point2d> &pts,
                                  std::vector<Vec3> &bl, std::vector<double> &d) const {
  std::vector<uint8_t> okl;
  bearings(pts, 0, bl, okl);
  d.assign(pts.size(), NaN);
  if (!right || pts.empty()) return;
  const cv::Mat img_r = pyr(*right);
  std::vector<cv::Point2d> pr;
  std::vector<uint8_t> ok;
  klt(img_l, img_r, pts, false, pr, ok);
  std::vector<Vec3> br;
  std::vector<uint8_t> okr, vl_ok, vr_ok;
  bearings(pr, 1, br, okr);
  std::vector<cv::Point2d> ul, ur;
  rect_uv(bl, 0, ul, vl_ok);
  rect_uv(br, 1, ur, vr_ok);
  for (size_t i = 0; i < pts.size(); ++i) {
    const double dd = ul[i].x - ur[i].x;
    if (ok[i] && okl[i] && okr[i] && vl_ok[i] && vr_ok[i] && std::abs(ul[i].y - ur[i].y) < cfg_.stereo_max_dy_px &&
        dd > -0.5)
      d[i] = dd;
  }
}

std::vector<Vec3> MotionEstimator::instance_depth(const std::vector<cv::Point2d> &pts, const std::vector<int> &tids,
                                                  const std::map<int, int> &tid_to_inst,
                                                  const std::vector<Instance> &instances, const std::vector<Vec3> &b,
                                                  const std::vector<double> &d_klt) const {
  std::vector<Vec3> X(pts.size(), Vec3(NaN, NaN, NaN));
  if (pts.empty()) return X;
  std::vector<double> d(pts.size(), NaN);
  std::set<int> uniq(tids.begin(), tids.end());
  for (int tid : uniq) {
    std::vector<size_t> sel;
    std::vector<double> v;
    for (size_t i = 0; i < tids.size(); ++i)
      if (tids[i] == tid) {
        sel.push_back(i);
        if (std::isfinite(d_klt[i]) && d_klt[i] > 0) v.push_back(d_klt[i]);
      }
    if (v.size() >= 3) {
      const double med = median_f64(v);
      for (size_t i : sel) {
        const double dk = d_klt[i];
        d[i] = cfg_.per_point_depth ? ((std::isfinite(dk) && std::abs(dk - med) < std::max(1.0, 0.3 * med)) ? dk : med)
                                    : med;
      }
    } else {
      auto it = tid_to_inst.find(tid);
      const double dm = it != tid_to_inst.end() ? instances[it->second].disparity : NaN;
      if (std::isfinite(dm) && dm > 0)
        for (size_t i : sel) d[i] = dm;
    }
  }
  for (size_t i = 0; i < pts.size(); ++i)
    if (std::isfinite(d[i]) && d[i] > 0) X[i] = point_from_disparity(b[i], d[i]);
  return X;
}

double mask_overlap(const Instance &a, const Instance &b) {
  const int x0 = std::max(a.bbox.x0, b.bbox.x0), y0 = std::max(a.bbox.y0, b.bbox.y0);
  const int x1 = std::min(a.bbox.x1, b.bbox.x1), y1 = std::min(a.bbox.y1, b.bbox.y1);
  if (x1 <= x0 || y1 <= y0) return 0.0;
  long inter = 0;
  for (int y = y0; y < y1; ++y) {
    const uint8_t *pa = a.mask.ptr<uint8_t>(y), *pb = b.mask.ptr<uint8_t>(y);
    for (int x = x0; x < x1; ++x) inter += (pa[x] && pb[x]);
  }
  if (inter == 0) return 0.0;
  return (double)inter / (double)std::max<long>(1, std::min(a.area(), b.area()));
}

// ------------------------------------------------------------------------------------------------ main
std::map<int, bool> MotionEstimator::update(const cv::Mat &left, const cv::Mat *right, double stamp,
                                            std::vector<Instance> &instances, const std::optional<Mat3> &R_imu) {
  const MotionConfig &c = cfg_;
  const auto t0 = Clock::now();
  frame_ += 1;
  const cv::Mat img_s = pyr(left);
  const cv::Mat &pyr_k = img_s;
  const double dt = prev_t_ ? stamp - *prev_t_ : 0.0;
  std::optional<Mat3> R_g;
  double gyro_sigma = c.gyro_sigma_rad;
  if (R_imu) R_g = R_CI_.t() * R_imu->t() * R_CI_;
  else if (!prev_pyr_.empty() && c.no_imu_sigma_rad > 0) {
    R_g = Mat3::eye();
    gyro_sigma = c.no_imu_sigma_rad;
  }
  std::vector<int> relevant;
  for (int i = 0; i < (int)instances.size(); ++i)
    if (instances[i].role == Role::Dynamic || instances[i].role == Role::Potential) relevant.push_back(i);
  if (c.min_bbox_px > 0) {
    std::vector<int> r2;
    for (int i : relevant) {
      const Box &b = instances[i].bbox;
      if (std::min(b.x1 - b.x0, b.y1 - b.y0) >= c.min_bbox_px) r2.push_back(i);
    }
    relevant.swap(r2);
  }
  MotionStats st;
  std::optional<EgoMotion> ego;
  std::map<int, InstFit> ev_by_tid;
  std::map<int, std::map<int, int>> votes;
  std::vector<cv::Point2d> new_in_p, bg_keep;
  std::vector<int> new_in_tid;
  std::vector<Vec3> new_in_X, bg_kX;
  std::vector<long long> bg_kage;
  std::vector<cv::Point2d> p1;
  std::vector<uint8_t> ok, Xok;
  std::vector<Vec3> b1;
  size_t nb = 0;
  int n_bok = 0;
  if (!prev_pyr_.empty() && R_g && 0 < dt && dt < 1.0) {
    std::vector<cv::Point2d> allp = bg_p_;
    allp.insert(allp.end(), in_p_.begin(), in_p_.end());
    nb = bg_p_.size();
    klt(prev_pyr_, pyr_k, allp, false, p1, ok);
    if (!in_p_.empty()) {
      std::vector<cv::Point2d> p1i(p1.begin() + nb, p1.end());
      std::vector<uint8_t> oki(ok.begin() + nb, ok.end()), fbr;
      fb_ok(prev_pyr_, pyr_k, in_p_, p1i, oki, fbr);
      for (size_t k = 0; k < fbr.size(); ++k) ok[nb + k] = ok[nb + k] && fbr[k];
    }
    std::vector<uint8_t> okb;
    bearings(p1, 0, b1, okb);
    for (size_t k = 0; k < ok.size(); ++k) ok[k] = ok[k] && okb[k];
    std::vector<Vec3> Xb, bb;
    for (size_t k = 0; k < nb; ++k)
      if (ok[k] && finite3(bg_X_[k])) {
        Xb.push_back(bg_X_[k]);
        bb.push_back(b1[k]);
      }
    n_bok = (int)Xb.size();
    EgoMotion ego_c = estimate_ego(Xb, bb, *R_g, dt, gyro_sigma);
    if (R_imu || ego_c.t_ok) ego = ego_c;
  }
  if (ego) {
    st.has_ego = true;
    st.n_bg = n_bok;
    st.n_inl = ego->n_inliers;
    st.t_ok = ego->t_ok;
    st.sigma_bg_px = round_ndigits(ego->sigma_bg * f_raw_, 3);
    for (int k = 0; k < 3; ++k) st.t[k] = round_ndigits(ego->t[k], 4);
    st.dtheta_deg = round_ndigits(norm3(ego->dtheta) * 180.0 / M_PI, 4);
    st.rot_deg = round_ndigits(norm3(so3_log(*R_g)) * 180.0 / M_PI, 3);
    st.gyro = (bool)R_imu;
    for (size_t k = 0; k < nb; ++k)
      if (ok[k]) {
        bg_keep.push_back(p1[k]);
        if (ego->t_ok) {
          bg_kX.push_back(matvec(ego->R, bg_X_[k]) + ego->t);
          bg_kage.push_back(bg_age_[k] + 1);
        } else {
          bg_kX.push_back(Vec3(NaN, NaN, NaN));
          bg_kage.push_back(1LL << 30);
        }
      }
    const size_t ni = in_p_.size();
    Xok.assign(ni, 0);
    std::vector<cv::Point2i> q(ni);
    for (size_t k = 0; k < ni; ++k) {
      const bool iok = ok[nb + k];
      Xok[k] = iok && finite3(in_X_[k]);
      if (iok) q[k] = cv::Point2i((int)std::nearbyint(p1[nb + k].x), (int)std::nearbyint(p1[nb + k].y));
    }
    for (int i : relevant) {
      const Instance &inst = instances[i];
      const Box &bx = inst.bbox;
      for (size_t k = 0; k < ni; ++k) {
        if (!ok[nb + k]) continue;
        if (q[k].x >= bx.x0 && q[k].x < bx.x1 && q[k].y >= bx.y0 && q[k].y < bx.y1 &&
            inst.mask.at<uint8_t>(q[k].y, q[k].x))
          votes[i][in_tid_[k]] += 1;
      }
    }
    for (size_t k = 0; k < ni; ++k)
      if (ok[nb + k]) {
        new_in_p.push_back(p1[nb + k]);
        new_in_tid.push_back(in_tid_[k]);
        new_in_X.push_back(matvec(ego->R, in_X_[k]) + ego->t);
      }
  } else {
    tracks_.clear();
  }
  last_ego_ = ego;
  if (ego && ego->t_ok && poses_.count(frame_ - 1)) {
    Mat4 Tk = Mat4::eye();
    for (int r = 0; r < 3; ++r) {
      for (int k = 0; k < 3; ++k) Tk(r, k) = ego->R(r, k);
      Tk(r, 3) = ego->t[r];
    }
    poses_[frame_] = poses_[frame_ - 1] * Tk.inv(cv::DECOMP_LU);
  } else {
    poses_.clear();
    poses_[frame_] = Mat4::eye();
    for (auto &kv : tracks_) kv.second.hist.clear();
  }
  const int keep_frames = c.window_long_s <= 0 ? 64 : 200;
  for (auto it = poses_.begin(); it != poses_.end();) {
    if (it->first < frame_ - keep_frames) it = poses_.erase(it);
    else ++it;
  }
  const auto t1 = Clock::now();

  // ---- association instance <-> motion track (greedy on votes, same role)
  std::vector<std::pair<int, int>> assign;  // insertion order (Python dict)
  std::map<int, int> assign_map;           // i -> tid
  std::set<int> used;
  {
    struct P {
      int n, mi, tid;
    };
    std::vector<P> pairs;
    for (auto &kv : votes)
      for (auto &tv : kv.second) pairs.push_back({tv.second, -kv.first, tv.first});
    std::sort(pairs.begin(), pairs.end(), [](const P &a, const P &b) {
      if (a.n != b.n) return a.n > b.n;
      if (a.mi != b.mi) return a.mi > b.mi;
      return a.tid > b.tid;
    });
    for (const auto &p : pairs) {
      const int i = -p.mi;
      auto it = tracks_.find(p.tid);
      if (p.n < 3 || assign_map.count(i) || used.count(p.tid) || it == tracks_.end() ||
          it->second.role != instances[i].role)
        continue;
      assign.emplace_back(i, p.tid);
      assign_map[i] = p.tid;
      used.insert(p.tid);
    }
  }
  {
    std::vector<int> free;
    for (int i : relevant)
      if (!assign_map.count(i)) free.push_back(i);
    if (!free.empty()) {
      struct C {
        double iou;
        int mi, tid;
      };
      std::vector<C> cand;
      for (int i : free)
        for (auto &kv : tracks_) {
          if (used.count(kv.first) || !kv.second.box) continue;
          const double iou = box_iou(instances[i].bbox, *kv.second.box);
          if (iou >= 0.3 && instances[i].role == kv.second.role) cand.push_back({iou, -i, kv.first});
        }
      std::sort(cand.begin(), cand.end(), [](const C &a, const C &b) {
        if (a.iou != b.iou) return a.iou > b.iou;
        if (a.mi != b.mi) return a.mi > b.mi;
        return a.tid > b.tid;
      });
      for (const auto &cd : cand) {
        if (assign_map.count(-cd.mi) || used.count(cd.tid)) continue;
        assign.emplace_back(-cd.mi, cd.tid);
        assign_map[-cd.mi] = cd.tid;
        used.insert(cd.tid);
      }
    }
  }
  if (ego) {
    std::vector<Group> groups;
    for (const auto &it : assign) {
      Group gr;
      gr.key = it.second;
      for (size_t k = 0; k < in_p_.size(); ++k)
        if (in_tid_[k] == it.second && Xok[k]) {
          gr.X.push_back(in_X_[k]);
          gr.b.push_back(b1[nb + k]);
        }
      groups.push_back(std::move(gr));
    }
    ev_by_tid = instance_fits(groups, *ego, dt);
  }
  const int N = (int)instances.size();
  std::vector<uint8_t> inter((size_t)N * N, 0);
  for (int a = 0; a < N; ++a)
    for (int b = 0; b < N; ++b) {
      const Box &A = instances[a].bbox, &B = instances[b].bbox;
      inter[(size_t)a * N + b] = std::min(A.x1, B.x1) > std::max(A.x0, B.x0) && std::min(A.y1, B.y1) > std::max(A.y0, B.y0);
    }
  std::vector<std::pair<int, int>> pre_dup;  // insertion order
  std::map<int, int> pre_dup_map;
  if (c.dup_overlap > 0) {
    for (int i : relevant) {
      if (assign_map.count(i)) continue;
      for (const auto &jt : assign) {
        const int j = jt.first;
        if (inter[(size_t)i * N + j] && instances[j].role == instances[i].role &&
            mask_overlap(instances[i], instances[j]) >= c.dup_overlap) {
          pre_dup.emplace_back(i, jt.second);
          pre_dup_map[i] = jt.second;
          break;
        }
      }
    }
  }
  for (int i : relevant) {
    if (assign_map.count(i) || pre_dup_map.count(i)) continue;
    const Instance &inst = instances[i];
    const double prior = inst.role == Role::Dynamic ? c.prior_dynamic : c.prior_potential;
    MotionTrack trk;
    trk.id = next_id_;
    trk.role = inst.role;
    trk.cls = inst.cls;
    trk.l = prior;
    trk.is_static = prior <= c.th_static;
    trk.is_moving = prior >= c.th_moving;
    tracks_[trk.id] = trk;
    next_id_ += 1;
    assign.emplace_back(i, trk.id);
    assign_map[i] = trk.id;
  }
  std::map<int, int> inv_assign;
  for (const auto &it : assign) inv_assign[it.second] = it.first;
  std::vector<const Instance *> a_inst;
  for (const auto &it : assign) a_inst.push_back(&instances[it.first]);
  const auto anchors_v = anchor_points(a_inst);
  std::map<int, std::optional<Vec3>> anchors;
  for (size_t k = 0; k < assign.size(); ++k) anchors[assign[k].first] = anchors_v[k];
  std::vector<int> tids;
  for (auto &kv : tracks_) tids.push_back(kv.first);
  const double hist_keep = std::max(c.window_max_s, c.window_long_s) + 0.05;
  for (int tid : tids) {
    MotionTrack &trk = tracks_[tid];
    auto ia = inv_assign.find(tid);
    std::optional<WinFit> win, win_long;
    if (ia != inv_assign.end()) {
      const auto &P = anchors[ia->second];
      if (P) {
        trk.hist.push_back({frame_, stamp, *P});
        std::vector<MotionTrack::Hist> h2;
        for (const auto &h : trk.hist)
          if (stamp - h.stamp <= hist_keep) h2.push_back(h);
        trk.hist.swap(h2);
        win = window_fit(trk, stamp, c.window_min_s, c.window_max_s);
        if (c.window_long_s > 0) win_long = window_fit(trk, stamp, 0.75 * c.window_long_s, c.window_long_s);
      }
    }
    std::optional<InstFit> ev;
    auto ie = ev_by_tid.find(tid);
    if (ie != ev_by_tid.end()) ev = ie->second;
    observe(trk, ev, win);
    trk.raw.valid = true;
    trk.raw.stamp = stamp;
    trk.raw.ev = ev;
    trk.raw.win = win;
    trk.raw.win_long = win_long;
    trk.raw.matched = ia != inv_assign.end();
    if (ia != inv_assign.end()) {
      trk.missing = 0;
      trk.box = instances[ia->second].bbox;
    } else {
      trk.missing += 1;
      if (trk.missing > c.max_missing) tracks_.erase(tid);
    }
  }
  std::map<int, int> dup;
  if (c.dup_overlap > 0) {
    std::vector<std::pair<int, int>> items = assign;
    std::stable_sort(items.begin(), items.end(), [](const auto &a, const auto &b) { return a.second < b.second; });
    for (size_t a = 0; a < items.size(); ++a) {
      const int i = items[a].first;
      for (size_t k = 0; k < a; ++k) {
        const int j = items[k].first;
        if (dup.count(j) || !inter[(size_t)i * N + j] || instances[i].role != instances[j].role) continue;
        if (mask_overlap(instances[i], instances[j]) >= c.dup_overlap) {
          dup[i] = items[k].second;
          break;
        }
      }
    }
  }
  for (const auto &kv : pre_dup) dup[kv.first] = kv.second;
  std::map<int, bool> decisions;
  std::vector<std::pair<int, int>> dl;
  for (const auto &it : assign) {
    auto d = dup.find(it.first);
    dl.emplace_back(it.first, d != dup.end() ? d->second : it.second);
  }
  for (const auto &it : pre_dup) dl.push_back(it);
  for (const auto &it : dl) {
    const int i = it.first, tid = it.second;
    auto tt = tracks_.find(tid);
    if (tt == tracks_.end()) continue;
    const MotionTrack &trk = tt->second;
    Instance &inst = instances[i];
    MotionInfo mi = trk.last;
    mi.id = tid;
    mi.state = trk.state();
    mi.l = round_ndigits(trk.l, 2);
    mi.dup = dup.count(i) > 0;
    inst.motion = mi;
    if (inst.role == Role::Dynamic) {
      if (c.use_still && trk.is_static) decisions[i] = false;
    } else {
      if (c.promote_moving && trk.is_moving) decisions[i] = true;
      else if (c.veto_static && trk.is_static) decisions[i] = false;
    }
  }
  const auto t2 = Clock::now();

  // ---- prepare frame k for the next step: instance points (keep + re-detect), background points
  {
    std::vector<cv::Point2d> p2;
    std::vector<int> t2v;
    std::vector<Vec3> X2;
    for (size_t k = 0; k < new_in_p.size(); ++k)
      if (tracks_.count(new_in_tid[k])) {
        p2.push_back(new_in_p[k]);
        t2v.push_back(new_in_tid[k]);
        X2.push_back(new_in_X[k]);
      }
    new_in_p.swap(p2);
    new_in_tid.swap(t2v);
    new_in_X.swap(X2);
  }
  std::map<int, int> tid_to_inst;
  for (const auto &it : assign) tid_to_inst[it.second] = it.first;
  {
    std::vector<uint8_t> keep(new_in_p.size(), 1);
    for (size_t k = 0; k < new_in_p.size(); ++k) {
      auto it = tid_to_inst.find(new_in_tid[k]);
      if (it == tid_to_inst.end()) continue;
      const int qx = (int)std::nearbyint(new_in_p[k].x), qy = (int)std::nearbyint(new_in_p[k].y);
      keep[k] = instances[it->second].mask.at<uint8_t>(qy, qx) != 0;
    }
    std::vector<cv::Point2d> p2;
    std::vector<int> t2v;
    std::vector<Vec3> X2;
    for (size_t k = 0; k < new_in_p.size(); ++k)
      if (keep[k]) {
        p2.push_back(new_in_p[k]);
        t2v.push_back(new_in_tid[k]);
        X2.push_back(new_in_X[k]);
      }
    new_in_p.swap(p2);
    new_in_tid.swap(t2v);
    new_in_X.swap(X2);
  }
  std::vector<cv::Point2d> in_p = new_in_p;
  std::vector<int> in_tid = new_in_tid;
  std::vector<Vec3> prop = new_in_X;
  const int er = (int)std::nearbyint(c.inst_erode_px * s_);
  for (int i : relevant) {
    auto it = assign_map.find(i);
    if (it == assign_map.end()) continue;
    const int tid = it->second;
    std::vector<cv::Point2d> existing;
    for (size_t k = 0; k < new_in_p.size(); ++k)
      if (new_in_tid[k] == tid) existing.push_back(new_in_p[k]);
    const int have = (int)existing.size();
    const int need = (int)c.inst_points - have;
    if (have >= c.redetect_ratio * c.inst_points || need <= 2) continue;
    auto pts = detect_in_instance(img_s, instances[i], need, er, existing);
    for (const auto &p : pts) {
      in_p.push_back(p);
      in_tid.push_back(tid);
      prop.push_back(Vec3(NaN, NaN, NaN));
    }
  }
  std::vector<Box> boxes;
  for (const auto &x : instances)
    if (x.role == Role::Dynamic || x.role == Role::Potential)
      boxes.push_back(expand_box(x.bbox, (int)c.bg_exclude_px, 0.0, rect_.cams[0].width, rect_.cams[0].height));
  if (!bg_keep.empty()) {
    std::vector<cv::Point2d> p2;
    std::vector<Vec3> X2;
    std::vector<long long> a2;
    for (size_t k = 0; k < bg_keep.size(); ++k) {
      bool out = false;
      for (const auto &b : boxes)
        out = out || (bg_keep[k].x >= b.x0 && bg_keep[k].x < b.x1 && bg_keep[k].y >= b.y0 && bg_keep[k].y < b.y1);
      if (!out) {
        p2.push_back(bg_keep[k]);
        X2.push_back(bg_kX[k]);
        a2.push_back(bg_kage[k]);
      }
    }
    bg_keep.swap(p2);
    bg_kX.swap(X2);
    bg_kage.swap(a2);
  }
  if ((double)bg_keep.size() < 0.8 * c.bg_points) {
    auto add = detect_background(img_s, boxes, bg_keep, (int)c.bg_points - (int)bg_keep.size());
    for (const auto &p : add) {
      bg_keep.push_back(p);
      bg_kX.push_back(Vec3(NaN, NaN, NaN));
      bg_kage.push_back(1LL << 30);
    }
  }
  std::vector<size_t> bidx, iidx;
  for (size_t k = 0; k < bg_keep.size(); ++k)
    if (!finite3(bg_kX[k]) || bg_kage[k] >= c.stereo_refresh) bidx.push_back(k);
  std::vector<uint8_t> imeas(in_p.size(), 0);
  {
    std::map<int, int> taken;
    for (size_t k = 0; k < in_p.size(); ++k)
      if (taken[in_tid[k]]++ < c.stereo_inst_points) imeas[k] = 1;
    for (size_t k = 0; k < in_p.size(); ++k)
      if (imeas[k]) iidx.push_back(k);
  }
  std::vector<cv::Point2d> spts;
  for (size_t k : bidx) spts.push_back(bg_keep[k]);
  for (size_t k : iidx) spts.push_back(in_p[k]);
  std::vector<Vec3> bl;
  std::vector<double> dlv;
  stereo_disp(pyr_k, right, spts, bl, dlv);
  const size_t nbm = bidx.size();
  std::vector<Vec3> bg_X = bg_kX;
  std::vector<long long> bg_age = bg_kage;
  for (size_t k = 0; k < nbm; ++k) {
    const size_t j = bidx[k];
    bg_X[j] = std::isfinite(dlv[k]) ? point_from_disparity(bl[k], std::max(dlv[k], 0.25)) : Vec3(NaN, NaN, NaN);
    bg_age[j] = 0;
  }
  std::vector<Vec3> bi(in_p.size(), Vec3(NaN, NaN, NaN));
  std::vector<double> di(in_p.size(), NaN);
  for (size_t k = 0; k < iidx.size(); ++k) {
    bi[iidx[k]] = bl[nbm + k];
    di[iidx[k]] = dlv[nbm + k];
  }
  {
    std::vector<cv::Point2d> pb;
    std::vector<size_t> ib;
    for (size_t k = 0; k < in_p.size(); ++k)
      if (!imeas[k]) {
        pb.push_back(in_p[k]);
        ib.push_back(k);
      }
    if (!pb.empty()) {
      std::vector<Vec3> bb;
      std::vector<uint8_t> okk;
      bearings(pb, 0, bb, okk);
      for (size_t k = 0; k < ib.size(); ++k) bi[ib[k]] = bb[k];
    }
  }
  std::vector<Vec3> in_X = instance_depth(in_p, in_tid, tid_to_inst, instances, bi, di);
  for (size_t k = 0; k < in_X.size(); ++k)
    if (!finite3(in_X[k]) && finite3(prop[k])) in_X[k] = prop[k];
  const auto t3 = Clock::now();
  bg_p_ = bg_keep;
  bg_X_ = bg_X;
  bg_age_ = bg_age;
  in_p_ = in_p;
  in_X_ = in_X;
  in_tid_ = in_tid;
  prev_pyr_ = pyr_k;
  prev_t_ = stamp;
  st.n_tracks = (int)tracks_.size();
  st.n_inst_pts = (int)in_p.size();
  st.ms_flow_ego = ms_since(t0, t1);
  st.ms_assoc = ms_since(t1, t2);
  st.ms_points = ms_since(t2, t3);
  stats_ = st;
  return decisions;
}

}  // namespace savior
