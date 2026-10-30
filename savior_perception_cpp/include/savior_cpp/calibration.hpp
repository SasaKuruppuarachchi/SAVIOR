// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/calibration.py: Kalibr/OpenVINS imu-cam chain + raw<->rect maps.
#pragma once

#include <map>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

namespace savior {

constexpr float INVALID_COORD = -1.0e5f;

struct CameraModel {
  cv::Matx33d K;
  cv::Vec4d D;
  std::string model;  // radtan | equidistant
  int width = 0, height = 0;
  cv::Matx44d T_cam_imu;
  std::string name, rostopic;
  bool is_fisheye() const { return model == "equidistant"; }
  // Nx2 raw pixels of Nx3 camera points (cv::projectPoints / cv::fisheye::projectPoints)
  std::vector<cv::Point2d> project(const std::vector<cv::Point3d> &pts) const;
  // raw px -> normalized undistorted coords + validity (reprojection within tol_px)
  void undistort_normalized(const std::vector<cv::Point2d> &pts, std::vector<cv::Point2d> &xy,
                            std::vector<uint8_t> &valid, double tol_px = 0.05) const;
};

std::map<std::string, CameraModel> load_kalibr_imucam_chain(const std::string &path);

class StereoRectifier {
 public:
  StereoRectifier(const CameraModel &cam0, const CameraModel &cam1, double focal_scale = 1.0, double size_scale = 0.0,
                  double max_scale = 2.0);
  CameraModel cams[2];
  cv::Matx44d T_c1_c0;
  cv::Matx33d R_rect[2];
  double baseline = 0, f = 0, cx = 0, cy = 0;
  int rect_w = 0, rect_h = 0;
  cv::Matx33d K_rect;
  cv::Mat raw_to_rect_x[2], raw_to_rect_y[2];  // CV_32F, raw size
  cv::Mat rect_to_raw_x[2], rect_to_raw_y[2];  // CV_32F, rect size
  double fb() const { return f * baseline; }

 private:
  void raw_normalized(int i, std::vector<double> &xn, std::vector<double> &yn, std::vector<uint8_t> &valid) const;
  void build_rect_to_raw(int i, double tol_rect_px = 1.0);
};

StereoRectifier stereo_from_kalibr(const std::string &path, const std::string &cam_left = "cam0",
                                   const std::string &cam_right = "cam1", double focal_scale = 1.0,
                                   double size_scale = 0.0, double max_scale = 2.0);

}  // namespace savior
