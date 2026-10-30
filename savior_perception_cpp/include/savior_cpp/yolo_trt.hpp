// SPDX-License-Identifier: GPL-3.0-or-later
// YOLO26-seg (Ultralytics export, end2end=false) instance segmentation through the TensorRT C++ API, reproducing the
// Ultralytics 8.4 predict path used by savior_perception/segmenters/yolo.py (retina_masks=true, fast_masks):
//   LetterBox(center, pad 114, INTER_LINEAR) -> BGR->RGB, x * (1/255) (torch div_ by a scalar = reciprocal multiply)
//   -> engine -> NMS (conf > thr on the best class, class filter, class-offset boxes 7680, stable score sort, IoU > iou)
//   -> scale_boxes (pad, gain, clip) -> process_mask_native (coeffs @ protos, [x f bilinear], slice + bilinear to the
//   image, > 0) -> crop_mask (float box) -> drop empty masks -> integer box crops (floor/ceil).
// The .engine files are the Ultralytics ones (4-byte length + JSON metadata header + serialized TensorRT engine).
#pragma once

#include <map>
#include <memory>
#include <string>
#include <vector>

#include <opencv2/core.hpp>

#include "savior_cpp/types.hpp"

namespace savior {

struct YoloOptions {
  std::string engine_path;
  double conf = 0.25;
  double iou = 0.7;
  int max_det = 300;
  std::vector<std::string> classes;  // empty = all classes; else names (case-insensitive)
  bool retina_masks = true;
};

struct YoloTimings {
  double pre = 0, infer = 0, nms = 0, masks = 0, total = 0;
};

class YoloTrtSegmenter {
 public:
  explicit YoloTrtSegmenter(const YoloOptions &opt);
  ~YoloTrtSegmenter();
  YoloTrtSegmenter(const YoloTrtSegmenter &) = delete;
  YoloTrtSegmenter &operator=(const YoloTrtSegmenter &) = delete;
  // image: RAW gray (CV_8UC1) or BGR (CV_8UC3). Returns instances with full-frame 0/1 masks and integer boxes.
  std::vector<Instance> predict(const cv::Mat &image);
  void warmup(int h, int w);
  const std::map<int, std::string> &names() const { return names_; }
  int input_h() const { return in_h_; }
  int input_w() const { return in_w_; }
  const YoloTimings &last_timings() const { return t_; }

 private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
  YoloOptions opt_;
  std::map<int, std::string> names_;
  std::vector<int> class_ids_;  // sorted; empty + filter -> no output
  bool filter_ = false;
  int in_h_ = 0, in_w_ = 0, nc_ = 0, nm_ = 0, na_ = 0, mh_ = 0, mw_ = 0;
  YoloTimings t_;
};

}  // namespace savior
