// orbslam3_bag_si: ORB-SLAM3 stereo-inertial on a ROS 1 bag, following Examples/Stereo-Inertial/stereo_inertial_euroc.cc
// (same IMU association, same frame-locked pacing: sleep (dt/rate - t_track) after each frame; no frame is dropped).
//
// usage: orbslam3_bag_si VOC SETTINGS BAG OUT_DIR [--start-offset S] [--rate R]
//                        [--left /cam0/image_raw] [--right /cam1/image_raw] [--imu /imu0]
// writes OUT_DIR/
//   traj_world_ns.txt     SaveTrajectoryEuRoC, all tracked frames, IMU (body) frame, gravity-aligned map world (patch P8)
//   traj_upstream_ns.txt  SaveTrajectoryEuRoC with upstream rebasing on the first keyframe (reference only)
//   traj_realtime.txt     causal per-frame output of TrackStereo (T_wb = T_cw^-1 T_cb), states OK/RECENTLY_LOST; TUM [s]
//   timing.csv            stamp, TrackStereo wall time [ms], #IMU samples, tracking state
//   frames.txt            exact stamps of the processed frames (to restore exact stamps of the ns outputs)
// The bag start offset follows `rosbag play -s`: messages with bag time < begin + S are skipped.
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <map>
#include <string>
#include <thread>
#include <vector>

#include <cv_bridge/cv_bridge.h>
#include <opencv2/core/core.hpp>
#include <rosbag/bag.h>
#include <rosbag/view.h>
#include <sensor_msgs/Image.h>
#include <sensor_msgs/Imu.h>

#include "System.h"

int main(int argc, char **argv) {
  if (argc < 5) {
    std::cerr << "usage: orbslam3_bag_si VOC SETTINGS BAG OUT_DIR [--start-offset S] [--rate R] [--left T] [--right T] [--imu T]\n";
    return 1;
  }
  std::string voc = argv[1], settings = argv[2], bagf = argv[3], out = argv[4];
  double start_offset = 0.0, rate = 1.0;
  std::string tl = "/cam0/image_raw", tr = "/cam1/image_raw", ti = "/imu0";
  for (int i = 5; i + 1 < argc; i += 2) {
    std::string k = argv[i], v = argv[i + 1];
    if (k == "--start-offset") start_offset = std::stod(v);
    else if (k == "--rate") rate = std::stod(v);
    else if (k == "--left") tl = v;
    else if (k == "--right") tr = v;
    else if (k == "--imu") ti = v;
    else { std::cerr << "unknown option " << k << "\n"; return 1; }
  }

  // T_b_c (cam0 -> IMU) from the settings, for the causal per-frame output
  cv::FileStorage fs(settings, cv::FileStorage::READ);
  if (!fs.isOpened()) { std::cerr << "cannot open settings\n"; return 1; }
  cv::Mat Tbc_cv; fs["IMU.T_b_c1"] >> Tbc_cv; Tbc_cv.convertTo(Tbc_cv, CV_32F);
  Eigen::Matrix4f Tbc_m; for (int r = 0; r < 4; ++r) for (int c = 0; c < 4; ++c) Tbc_m(r, c) = Tbc_cv.at<float>(r, c);
  Sophus::SE3f Tbc(Eigen::Quaternionf(Tbc_m.block<3, 3>(0, 0)).normalized(), Tbc_m.block<3, 1>(0, 3));
  Sophus::SE3f Tcb = Tbc.inverse();

  rosbag::Bag bag; bag.open(bagf, rosbag::bagmode::Read);
  ros::Time t_begin;
  { rosbag::View all(bag); t_begin = all.getBeginTime(); }
  ros::Time t_from = t_begin + ros::Duration(start_offset);

  // IMU: all samples with bag time >= start, sorted by header stamp
  struct Imu { double t; float ax, ay, az, gx, gy, gz; };
  std::vector<Imu> imu;
  {
    rosbag::View v(bag, rosbag::TopicQuery(std::vector<std::string>{ti}), t_from);
    for (const rosbag::MessageInstance &m : v) {
      auto p = m.instantiate<sensor_msgs::Imu>(); if (!p) continue;
      imu.push_back({p->header.stamp.toSec(), (float)p->linear_acceleration.x, (float)p->linear_acceleration.y,
                     (float)p->linear_acceleration.z, (float)p->angular_velocity.x, (float)p->angular_velocity.y,
                     (float)p->angular_velocity.z});
    }
    std::stable_sort(imu.begin(), imu.end(), [](const Imu &a, const Imu &b) { return a.t < b.t; });
  }
  // stereo pairs (exact header-stamp match), in stamp order
  std::map<uint64_t, std::pair<cv::Mat, cv::Mat>> pairs;  // converted to mono8 at load (cv_bridge, as VINS-Fusion)
  {
    rosbag::View v(bag, rosbag::TopicQuery(std::vector<std::string>{tl, tr}), t_from);
    for (const rosbag::MessageInstance &m : v) {
      auto p = m.instantiate<sensor_msgs::Image>(); if (!p) continue;
      auto &e = pairs[p->header.stamp.toNSec()];
      cv::Mat g = cv_bridge::toCvCopy(p, "mono8")->image;
      if (m.getTopic() == tl) e.first = g; else e.second = g;
    }
  }
  std::vector<std::pair<uint64_t, std::pair<cv::Mat, cv::Mat>>> frames;
  for (auto &kv : pairs) if (!kv.second.first.empty() && !kv.second.second.empty()) frames.push_back(kv);
  std::cout << "[orbslam3_bag_si] " << frames.size() << " stereo pairs, " << imu.size() << " IMU samples, offset "
            << start_offset << " s, rate " << rate << std::endl;
  if (frames.empty() || imu.empty()) return 1;

  size_t first_imu = 0;  // as in the EuRoC example: last IMU sample <= first frame is the first one considered
  double t0 = frames[0].first * 1e-9;
  while (first_imu < imu.size() && imu[first_imu].t <= t0) first_imu++;
  if (first_imu > 0) first_imu--;

  ORB_SLAM3::System SLAM(voc, settings, ORB_SLAM3::System::IMU_STEREO, false);

  std::ofstream ftim(out + "/timing.csv"), frt(out + "/traj_realtime.txt"), ffr(out + "/frames.txt");
  ftim << "stamp,ms,n_imu,state\n";
  frt << "# timestamp tx ty tz qx qy qz qw\n";
  std::vector<ORB_SLAM3::IMU::Point> vImu;
  for (size_t ni = 0; ni < frames.size(); ++ni) {
    uint64_t ns = frames[ni].first;
    double tf = ns * 1e-9;
    const cv::Mat &L = frames[ni].second.first, &R = frames[ni].second.second;
    vImu.clear();
    if (ni > 0)
      while (first_imu < imu.size() && imu[first_imu].t <= tf) {
        const Imu &s = imu[first_imu];
        vImu.push_back(ORB_SLAM3::IMU::Point(s.ax, s.ay, s.az, s.gx, s.gy, s.gz, s.t));
        first_imu++;
      }
    auto c1 = std::chrono::steady_clock::now();
    Sophus::SE3f Tcw = SLAM.TrackStereo(L, R, tf, vImu);
    auto c2 = std::chrono::steady_clock::now();
    double tt = std::chrono::duration_cast<std::chrono::duration<double>>(c2 - c1).count();
    int st = SLAM.GetTrackingState();
    char sbuf[32]; std::snprintf(sbuf, sizeof sbuf, "%lu.%09lu", (unsigned long)(ns / 1000000000ULL), (unsigned long)(ns % 1000000000ULL));
    ftim << sbuf << "," << tt * 1e3 << "," << vImu.size() << "," << st << "\n";
    ffr << sbuf << "\n";
    if (st == 2 || st == 3) {  // OK, RECENTLY_LOST
      Sophus::SE3f Twb = Tcw.inverse() * Tcb;
      Eigen::Quaternionf q = Twb.unit_quaternion(); Eigen::Vector3f p = Twb.translation();
      char buf[256];
      std::snprintf(buf, sizeof buf, "%s %.6f %.6f %.6f %.9f %.9f %.9f %.9f\n", sbuf, p.x(), p.y(), p.z(), q.x(), q.y(), q.z(), q.w());
      frt << buf;
    }
    double T = (ni + 1 < frames.size()) ? (frames[ni + 1].first * 1e-9 - tf) : (ni > 0 ? tf - frames[ni - 1].first * 1e-9 : 0.0);
    T /= rate;
    if (tt < T) std::this_thread::sleep_for(std::chrono::duration<double>(T - tt));
  }
  ftim.close(); frt.close(); ffr.close();
  SLAM.Shutdown();
  unsetenv("ORBSLAM3_SAVE_IN_WORLD");
  SLAM.SaveTrajectoryEuRoC(out + "/traj_upstream_ns.txt");
  setenv("ORBSLAM3_SAVE_IN_WORLD", "1", 1);
  SLAM.SaveTrajectoryEuRoC(out + "/traj_world_ns.txt");
  std::cout << "[orbslam3_bag_si] done" << std::endl;
  std::fflush(nullptr);
  std::_Exit(0);  // skip static destructors (ORB-SLAM3 threads are never joined upstream)
}
