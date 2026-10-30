// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/calibration.hpp"
#include "savior_cpp/types.hpp"

#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>

#include <opencv2/calib3d.hpp>
#include <opencv2/imgproc.hpp>
#include <yaml-cpp/yaml.h>

namespace savior {

static const cv::TermCriteria ITER_CRITERIA(cv::TermCriteria::COUNT | cv::TermCriteria::EPS, 100, 1e-10);

std::vector<cv::Point2d> CameraModel::project(const std::vector<cv::Point3d> &pts) const {
  std::vector<cv::Point2d> out;
  if (pts.empty()) return out;
  cv::Mat rvec = cv::Mat::zeros(3, 1, CV_64F), tvec = cv::Mat::zeros(3, 1, CV_64F);
  cv::Mat obj(pts.size(), 1, CV_64FC3, (void *)pts.data());
  cv::Mat img;
  if (is_fisheye())
    cv::fisheye::projectPoints(obj, img, rvec, tvec, cv::Mat(K), cv::Mat(D));
  else
    cv::projectPoints(obj, rvec, tvec, cv::Mat(K), cv::Mat(D), img);
  out.resize(pts.size());
  for (size_t i = 0; i < pts.size(); ++i) {
    const double *p = img.ptr<double>((int)i);
    out[i] = cv::Point2d(p[0], p[1]);
  }
  return out;
}

void CameraModel::undistort_normalized(const std::vector<cv::Point2d> &pts, std::vector<cv::Point2d> &xy,
                                       std::vector<uint8_t> &valid, double tol_px) const {
  const size_t n = pts.size();
  xy.assign(n, cv::Point2d(0, 0));
  valid.assign(n, 0);
  if (!n) return;
  cv::Mat src(n, 1, CV_64FC2, (void *)pts.data());
  cv::Mat dst;
  if (is_fisheye()) {
#if CV_VERSION_MAJOR > 4 || (CV_VERSION_MAJOR == 4 && CV_VERSION_MINOR >= 7)
    cv::fisheye::undistortPoints(src, dst, cv::Mat(K), cv::Mat(D), cv::noArray(), cv::noArray(), ITER_CRITERIA);
#else
    cv::fisheye::undistortPoints(src, dst, cv::Mat(K), cv::Mat(D));
#endif
  } else {
    cv::undistortPoints(src, dst, cv::Mat(K), cv::Mat(D), cv::noArray(), cv::noArray(), ITER_CRITERIA);
  }
  std::vector<cv::Point3d> rays(n);
  std::vector<uint8_t> finite(n);
  for (size_t i = 0; i < n; ++i) {
    const double *p = dst.ptr<double>((int)i);
    finite[i] = std::isfinite(p[0]) && std::isfinite(p[1]);
    xy[i] = finite[i] ? cv::Point2d(p[0], p[1]) : cv::Point2d(0, 0);
    rays[i] = cv::Point3d(xy[i].x, xy[i].y, 1.0);
  }
  auto re = project(rays);
  for (size_t i = 0; i < n; ++i) {
    double dx = re[i].x - pts[i].x, dy = re[i].y - pts[i].y;
    valid[i] = finite[i] && std::sqrt(dx * dx + dy * dy) < tol_px;
  }
}

static std::string strip_opencv_yaml(const std::string &text) {
  std::istringstream in(text);
  std::ostringstream out;
  std::string line;
  bool first = true;
  while (std::getline(in, line)) {
    size_t a = line.find_first_not_of(" \t");
    if (a != std::string::npos && line[a] == '%') continue;
    if (!first) out << "\n";
    out << line;
    first = false;
  }
  return out.str();
}

std::map<std::string, CameraModel> load_kalibr_imucam_chain(const std::string &path) {
  std::ifstream f(path);
  if (!f) throw std::runtime_error("cannot open " + path);
  std::stringstream ss;
  ss << f.rdbuf();
  YAML::Node data = YAML::Load(strip_opencv_yaml(ss.str()));
  std::map<std::string, CameraModel> cams;
  for (auto it : data) {
    const std::string key = it.first.as<std::string>();
    if (key.rfind("cam", 0) != 0) continue;
    YAML::Node c = it.second;
    auto mat44 = [](const YAML::Node &n) {
      cv::Matx44d M;
      for (int r = 0; r < 4; ++r)
        for (int k = 0; k < 4; ++k) M(r, k) = n[r][k].as<double>();
      return M;
    };
    CameraModel m;
    if (c["T_cam_imu"]) m.T_cam_imu = mat44(c["T_cam_imu"]);
    else if (c["T_imu_cam"]) m.T_cam_imu = mat44(c["T_imu_cam"]).inv(cv::DECOMP_LU);
    else throw std::invalid_argument(path + ":" + key + ": neither T_cam_imu nor T_imu_cam present");
    std::string model = c["camera_model"] ? c["camera_model"].as<std::string>() : "pinhole";
    if (model != "pinhole") throw std::invalid_argument(path + ":" + key + ": camera_model '" + model + "' unsupported");
    auto in = c["intrinsics"];
    m.K = cv::Matx33d(in[0].as<double>(), 0, in[2].as<double>(), 0, in[1].as<double>(), in[3].as<double>(), 0, 0, 1.0);
    auto dc = c["distortion_coeffs"];
    if (dc.size() != 4) throw std::invalid_argument("expected 4 distortion coefficients");
    for (int k = 0; k < 4; ++k) m.D[k] = dc[k].as<double>();
    m.model = c["distortion_model"] ? c["distortion_model"].as<std::string>() : "radtan";
    if (m.model != "radtan" && m.model != "equidistant")
      throw std::invalid_argument("unsupported distortion_model '" + m.model + "' (radtan|equidistant)");
    m.width = c["resolution"][0].as<int>();
    m.height = c["resolution"][1].as<int>();
    m.name = key;
    m.rostopic = c["rostopic"] ? c["rostopic"].as<std::string>() : "";
    cams[key] = m;  // std::map: sorted keys like the Python loader
  }
  if (cams.empty()) throw std::invalid_argument(path + ": no cam* entries");
  return cams;
}

StereoRectifier::StereoRectifier(const CameraModel &cam0, const CameraModel &cam1, double focal_scale,
                                 double size_scale, double max_scale) {
  cams[0] = cam0;
  cams[1] = cam1;
  cv::Matx44d T0inv = cam0.T_cam_imu.inv(cv::DECOMP_LU);
  T_c1_c0 = cam1.T_cam_imu * T0inv;
  cv::Matx33d R;
  cv::Vec3d T;
  for (int r = 0; r < 3; ++r) {
    for (int k = 0; k < 3; ++k) R(r, k) = T_c1_c0(r, k);
    T[r] = T_c1_c0(r, 3);
  }
  const int w = cam0.width, h = cam0.height;
  cv::Mat R0, R1, P0, P1, Q;
  cv::stereoRectify(cv::Mat(cam0.K), cv::Mat::zeros(4, 1, CV_64F), cv::Mat(cam1.K), cv::Mat::zeros(4, 1, CV_64F),
                    cv::Size(w, h), cv::Mat(R), cv::Mat(T), R0, R1, P0, P1, Q, cv::CALIB_ZERO_DISPARITY, -1);
  R_rect[0] = cv::Matx33d((double *)R0.ptr<double>());
  R_rect[1] = cv::Matx33d((double *)R1.ptr<double>());
  cv::Vec3d T_rect = R_rect[1] * T;
  if (std::abs(T_rect[0]) < 10 * std::max({std::abs(T_rect[1]), std::abs(T_rect[2]), 1e-9}))
    throw std::invalid_argument("only horizontal stereo pairs are supported");
  if (T_rect[0] >= 0) throw std::invalid_argument("cam1 must be to the right of cam0 (expected T_rect.x < 0)");
  baseline = std::sqrt(T[0] * T[0] + T[1] * T[1] + T[2] * T[2]);
  double s4 = 0.0;
  s4 += cam0.K(0, 0); s4 += cam0.K(1, 1); s4 += cam1.K(0, 0); s4 += cam1.K(1, 1);
  f = focal_scale * (s4 / 4.0);
  std::vector<double> xn[2], yn[2];
  std::vector<uint8_t> val[2];
  for (int i = 0; i < 2; ++i) raw_normalized(i, xn[i], yn[i], val[i]);
  if (size_scale > 0) {
    rect_w = (int)std::nearbyint(w * size_scale);
    rect_h = (int)std::nearbyint(h * size_scale);
    cx = (rect_w - 1) / 2.0;
    cy = (rect_h - 1) / 2.0;
  } else {
    double xmin = Inf, xmax = -Inf, ymin = Inf, ymax = -Inf;
    for (int i = 0; i < 2; ++i)
      for (size_t k = 0; k < xn[i].size(); ++k)
        if (val[i][k]) {
          xmin = std::min(xmin, xn[i][k]); xmax = std::max(xmax, xn[i][k]);
          ymin = std::min(ymin, yn[i][k]); ymax = std::max(ymax, yn[i][k]);
        }
    double capx = max_scale * w / (2.0 * f), capy = max_scale * h / (2.0 * f);
    double x0 = std::max(xmin, -capx), x1 = std::min(xmax, capx);
    double y0 = std::max(ymin, -capy), y1 = std::min(ymax, capy);
    rect_w = (int)std::ceil((x1 - x0) * f - 1e-6) + 1;
    rect_h = (int)std::ceil((y1 - y0) * f - 1e-6) + 1;
    cx = -x0 * f;
    cy = -y0 * f;
  }
  K_rect = cv::Matx33d(f, 0, cx, 0, f, cy, 0, 0, 1.0);
  for (int i = 0; i < 2; ++i) {
    const int cw = cams[i].width, ch = cams[i].height;
    raw_to_rect_x[i].create(ch, cw, CV_32F);
    raw_to_rect_y[i].create(ch, cw, CV_32F);
    float *mx = raw_to_rect_x[i].ptr<float>(), *my = raw_to_rect_y[i].ptr<float>();
    for (size_t k = 0; k < (size_t)cw * ch; ++k) {
      mx[k] = val[i][k] ? (float)(f * xn[i][k] + cx) : INVALID_COORD;
      my[k] = val[i][k] ? (float)(f * yn[i][k] + cy) : INVALID_COORD;
    }
  }
  for (int i = 0; i < 2; ++i) build_rect_to_raw(i);
}

void StereoRectifier::raw_normalized(int i, std::vector<double> &xn, std::vector<double> &yn,
                                     std::vector<uint8_t> &valid) const {
  const CameraModel &cam = cams[i];
  const int w = cam.width, h = cam.height;
  std::vector<cv::Point2d> pts((size_t)w * h);
  for (int y = 0; y < h; ++y)
    for (int x = 0; x < w; ++x) pts[(size_t)y * w + x] = cv::Point2d(x, y);
  std::vector<cv::Point2d> xy;
  cam.undistort_normalized(pts, xy, valid);
  const cv::Matx33d &R = R_rect[i];
  xn.resize(pts.size());
  yn.resize(pts.size());
  for (size_t k = 0; k < pts.size(); ++k) {
    const double a = xy[k].x, b = xy[k].y;
    const double r0 = a * R(0, 0) + b * R(0, 1) + 1.0 * R(0, 2);
    const double r1 = a * R(1, 0) + b * R(1, 1) + 1.0 * R(1, 2);
    const double r2 = a * R(2, 0) + b * R(2, 1) + 1.0 * R(2, 2);
    valid[k] = valid[k] && r2 > 1e-6;
    const double zs = valid[k] ? r2 : 1.0;
    xn[k] = r0 / zs;
    yn[k] = r1 / zs;
  }
}

void StereoRectifier::build_rect_to_raw(int i, double tol_rect_px) {
  const CameraModel &cam = cams[i];
  cv::Mat mx, my;
  cv::Size rs(rect_w, rect_h);
  if (cam.is_fisheye())
    cv::fisheye::initUndistortRectifyMap(cv::Mat(cam.K), cv::Mat(cam.D), cv::Mat(R_rect[i]), cv::Mat(K_rect), rs,
                                         CV_32FC1, mx, my);
  else
    cv::initUndistortRectifyMap(cv::Mat(cam.K), cv::Mat(cam.D), cv::Mat(R_rect[i]), cv::Mat(K_rect), rs, CV_32FC1, mx,
                                my);
  const int w = cam.width, h = cam.height;
  cv::Mat inside(rs, CV_8U), mxs(rs, CV_32F), mys(rs, CV_32F);
  for (int y = 0; y < rect_h; ++y)
    for (int x = 0; x < rect_w; ++x) {
      float a = mx.at<float>(y, x), b = my.at<float>(y, x);
      bool in = std::isfinite(a) && std::isfinite(b) && a >= -0.5f && a <= (float)(w - 0.5) && b >= -0.5f &&
                b <= (float)(h - 0.5);
      inside.at<uint8_t>(y, x) = in;
      mxs.at<float>(y, x) = in ? a : -1.0f;
      mys.at<float>(y, x) = in ? b : -1.0f;
    }
  cv::Mat bu, bv;
  cv::remap(raw_to_rect_x[i], bu, mxs, mys, cv::INTER_LINEAR, cv::BORDER_REPLICATE);
  cv::remap(raw_to_rect_y[i], bv, mxs, mys, cv::INTER_LINEAR, cv::BORDER_REPLICATE);
  for (int y = 0; y < rect_h; ++y)
    for (int x = 0; x < rect_w; ++x) {
      bool ok = inside.at<uint8_t>(y, x) && std::abs(bu.at<float>(y, x) - (float)x) < (float)tol_rect_px &&
                std::abs(bv.at<float>(y, x) - (float)y) < (float)tol_rect_px;
      if (!ok) {
        mx.at<float>(y, x) = INVALID_COORD;
        my.at<float>(y, x) = INVALID_COORD;
      }
    }
  rect_to_raw_x[i] = mx;
  rect_to_raw_y[i] = my;
}

StereoRectifier stereo_from_kalibr(const std::string &path, const std::string &cam_left, const std::string &cam_right,
                                   double focal_scale, double size_scale, double max_scale) {
  auto cams = load_kalibr_imucam_chain(path);
  if (!cams.count(cam_left) || !cams.count(cam_right)) throw std::invalid_argument("camera not in " + path);
  return StereoRectifier(cams.at(cam_left), cams.at(cam_right), focal_scale, size_scale, max_scale);
}

}  // namespace savior
