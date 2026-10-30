// P4 harness: TrackKLT with use_dynamic_mask-style gating + all-zero dynamic masks vs gating off.
// usage: compat_harness <off|gate0|compat0|compat_dyn> <static:none|lr> <out.txt>
// Fast camera motion (features leave the image -> out-of-bounds tracks) and different left/right static masks
// (as OpenLORIS) exercise every SAVIOR deviation from upstream.
#include <cstdio>
#include <fstream>
#include <memory>
#include <random>
#include <unordered_map>
#include <opencv2/opencv.hpp>
#include "cam/CamRadtan.h"
#include "track/TrackKLT.h"
#include "utils/print.h"
using namespace ov_core;
static const int W = 752, H = 480, DISP = 12;

int main(int argc, char **argv) {
  if (argc < 4) return 1;
  std::string mode = argv[1], stat = argv[2];
  ov_core::Printer::setPrintLevel("WARNING");
  std::unordered_map<size_t, std::shared_ptr<CamBase>> cams;
  for (size_t i = 0; i < 2; i++) {
    auto cam = std::make_shared<CamRadtan>(W, H);
    Eigen::VectorXd calib = Eigen::VectorXd::Zero(8);
    calib << 458.0, 457.0, 367.0, 248.0, 0, 0, 0, 0;
    cam->set_value(calib);
    cams.insert({i, cam});
  }
  cv::setNumThreads(1);
  TrackKLT trk(cams, 150, 0, true, TrackBase::HISTOGRAM, 20, 5, 5, 10);
  if (mode != "off") {
    trk.set_mask_gating(true, 128, 224, 30, 75);
    trk.set_mask_compat(mode.rfind("compat", 0) == 0);
  }
  cv::Mat tex(H + 600, W + 900, CV_8UC1);
  std::mt19937 rng(7);
  cv::randu(tex, 0, 255);
  cv::GaussianBlur(tex, tex, cv::Size(0, 0), 3.0);
  cv::normalize(tex, tex, 0, 255, cv::NORM_MINMAX);
  std::uniform_int_distribution<int> ux(0, tex.cols), uy(0, tex.rows), ur(3, 15), uc(0, 255);
  for (int i = 0; i < 4000; i++) cv::circle(tex, cv::Point(ux(rng), uy(rng)), ur(rng), cv::Scalar(uc(rng)), -1);
  cv::Mat s0 = cv::Mat::zeros(H, W, CV_8UC1), s1 = cv::Mat::zeros(H, W, CV_8UC1);
  if (stat == "lr") {  // different static masks per camera (upstream uses mask0 for right detections)
    s0(cv::Rect(0, H - 60, W, 60)).setTo(255);
    s1(cv::Rect(W - 90, 0, 90, H)).setTo(255);
  }
  std::ofstream out(argv[3]);
  int core_hits = 0;
  for (int k = 0; k < 150; k++) {
    double ox = 100.0 + 3.3 * k + 20 * std::sin(0.11 * k), oy = 80.0 + 1.7 * k;   // features leave the image
    cv::Mat A0 = (cv::Mat_<double>(2, 3) << 1, 0, -ox, 0, 1, -oy);
    cv::Mat A1 = (cv::Mat_<double>(2, 3) << 1, 0, -(ox + DISP), 0, 1, -oy);
    cv::Mat img0, img1;
    cv::warpAffine(tex, img0, A0, cv::Size(W, H), cv::INTER_LINEAR);
    cv::warpAffine(tex, img1, A1, cv::Size(W, H), cv::INTER_LINEAR);
    cv::Mat d0 = cv::Mat::zeros(H, W, CV_8UC1), d1 = cv::Mat::zeros(H, W, CV_8UC1);
    if (mode == "compat_dyn" && k >= 40 && k < 90) {
      d0(cv::Rect(300, 150, 160, 180)).setTo(255);
      d1(cv::Rect(300 - DISP, 150, 160, 180)).setTo(255);
    }
    CameraData msg;
    msg.timestamp = 1000.0 + 0.05 * k;
    msg.sensor_ids = {0, 1};
    msg.images = {img0, img1};
    msg.masks = {s0, s1};
    if (mode != "off") msg.masks_dynamic = {d0, d1};
    trk.feed_new_camera(msg);
    auto obs = trk.get_last_obs();
    auto ids = trk.get_last_ids();
    for (size_t c = 0; c < 2; c++) {
      const cv::Mat &d = (c == 0) ? d0 : d1;
      for (size_t i = 0; i < obs[c].size(); i++) {
        const auto &pt = obs[c].at(i).pt;
        out << k << " " << c << " " << ids[c].at(i) << " " << cv::format("%.5f %.5f", pt.x, pt.y) << "\n";
        int x = (int)pt.x, y = (int)pt.y;
        if (x >= 0 && y >= 0 && x < W && y < H && d.at<uint8_t>(y, x) == 255) core_hits++;
      }
    }
  }
  printf("%s %s: features in the dynamic core: %d\n", mode.c_str(), stat.c_str(), core_hits);
  return 0;
}
