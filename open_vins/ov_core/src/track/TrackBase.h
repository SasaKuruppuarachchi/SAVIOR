/*
 * OpenVINS: An Open Platform for Visual-Inertial Research
 * Copyright (C) 2018-2023 Patrick Geneva
 * Copyright (C) 2018-2023 Guoquan Huang
 * Copyright (C) 2018-2023 OpenVINS Contributors
 * Copyright (C) 2018-2019 Kevin Eckenhoff
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#ifndef OV_CORE_TRACK_BASE_H
#define OV_CORE_TRACK_BASE_H

#include <atomic>
#include <fstream>
#include <iostream>
#include <mutex>
#include <thread>
#include <unordered_map>

#include <boost/date_time/posix_time/posix_time.hpp>
#include <opencv2/core/core.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/opencv.hpp>

#include "utils/colors.h"
#include "utils/print.h"
#include "utils/sensor_data.h"

namespace ov_core {

class Feature;
class CamBase;
class FeatureDatabase;

/**
 * @brief Visual feature tracking base class
 *
 * This is the base class for all our visual trackers.
 * The goal here is to provide a common interface so all underlying trackers can simply hide away all the complexities.
 * We have something called the "feature database" which has all the tracking information inside of it.
 * The user can ask this database for features which can then be used in an MSCKF or batch-based setting.
 * The feature tracks store both the raw (distorted) and undistorted/normalized values.
 * Right now we just support two camera models, see: undistort_point_brown() and undistort_point_fisheye().
 *
 * @m_class{m-note m-warning}
 *
 * @par A Note on Multi-Threading Support
 * There is some support for asynchronous multi-threaded feature tracking of independent cameras.
 * The key assumption during implementation is that the user will not try to track on the same camera in parallel, and instead call on
 * different cameras. For example, if I have two cameras, I can either sequentially call the feed function, or I spin each of these into
 * separate threads and wait for their return. The @ref currid is atomic to allow for multiple threads to access it without issue and ensure
 * that all features have unique id values. We also have mutex for access for the calibration and previous images and tracks (used during
 * visualization). It should be noted that if a thread calls visualization, it might hang or the feed thread might, due to acquiring the
 * mutex for that specific camera id / feed.
 *
 * This base class also handles most of the heavy lifting with the visualization, but the sub-classes can override
 * this and do their own logic if they want (i.e. the TrackAruco has its own logic for visualization).
 * This visualization needs access to the prior images and their tracks, thus must synchronise in the case of multi-threading.
 * This shouldn't impact performance, but high frequency visualization calls can negatively effect the performance.
 */
class TrackBase {

public:
  /**
   * @brief Desired pre-processing image method.
   */
  enum HistogramMethod { NONE, HISTOGRAM, CLAHE };

  /**
   * @brief Public constructor with configuration variables
   * @param cameras camera calibration object which has all camera intrinsics in it
   * @param numfeats number of features we want want to track (i.e. track 200 points from frame to frame)
   * @param numaruco the max id of the arucotags, so we ensure that we start our non-auroc features above this value
   * @param stereo if we should do stereo feature tracking or binocular
   * @param histmethod what type of histogram pre-processing should be done (histogram eq?)
   */
  TrackBase(std::unordered_map<size_t, std::shared_ptr<CamBase>> cameras, int numfeats, int numaruco, bool stereo,
            HistogramMethod histmethod);

  virtual ~TrackBase() {}

  /**
   * @brief Process a new image
   * @param message Contains our timestamp, images, and camera ids
   */
  virtual void feed_new_camera(const CameraData &message) = 0;

  /**
   * @brief Shows features extracted in the last image
   * @param img_out image to which we will overlayed features on
   * @param r1,g1,b1 first color to draw in
   * @param r2,g2,b2 second color to draw in
   * @param overlay Text overlay to replace to normal "cam0" in the top left of screen
   */
  virtual void display_active(cv::Mat &img_out, int r1, int g1, int b1, int r2, int g2, int b2, std::string overlay = "");

  /**
   * @brief Shows a "trail" for each feature (i.e. its history)
   * @param img_out image to which we will overlayed features on
   * @param r1,g1,b1 first color to draw in
   * @param r2,g2,b2 second color to draw in
   * @param highlighted unique ids which we wish to highlight (e.g. slam feats)
   * @param overlay Text overlay to replace to normal "cam0" in the top left of screen
   */
  virtual void display_history(cv::Mat &img_out, int r1, int g1, int b1, int r2, int g2, int b2, std::vector<size_t> highlighted = {},
                               std::string overlay = "");

  /**
   * @brief Get the feature database with all the track information
   * @return FeatureDatabase pointer that one can query for features
   */
  std::shared_ptr<FeatureDatabase> get_feature_database() { return database; }

  /**
   * @brief Changes the ID of an actively tracked feature to another one.
   *
   * This function can be helpfull if you detect a loop-closure with an old frame.
   * One could then change the id of an active feature to match the old feature id!
   *
   * @param id_old Old id we want to change
   * @param id_new Id we want to change the old id to
   */
  void change_feat_id(size_t id_old, size_t id_new);

  /// Getter method for active features in the last frame (observations per camera)
  std::unordered_map<size_t, std::vector<cv::KeyPoint>> get_last_obs() {
    std::lock_guard<std::mutex> lckv(mtx_last_vars);
    return pts_last;
  }

  /// Getter method for active features in the last frame (ids per camera)
  std::unordered_map<size_t, std::vector<size_t>> get_last_ids() {
    std::lock_guard<std::mutex> lckv(mtx_last_vars);
    return ids_last;
  }

  /// Getter method for number of active features
  int get_num_features() { return num_features; }

  /// Setter method for number of active features
  void set_num_features(int _num_features) { num_features = _num_features; }

  /**
   * @brief SAVIOR: enable layered (dynamic) mask gating.
   *
   * When enabled, every mask is binarized at the tracker entry so that a pixel is rejected iff its value is >= threshold.
   * This keeps every downstream test of the upstream code (point tests, FAST/GRID griders, coarse grid check) consistent.
   * The KLT tracker additionally rejects already-tracked features in the stereo path (left and right) and relaxes the
   * threshold to relaxed_threshold for a camera whose number of kept features would fall below min_features.
   * When disabled (default) the masks are passed through untouched, i.e. upstream behaviour.
   *
   * @param enabled If gating should be enabled
   * @param threshold Pixel values >= threshold are rejected (1..256, 256 = never reject / observe only)
   * @param relaxed_threshold Threshold used for relaxation (>= threshold, 256 = never reject)
   * @param min_features Per-camera number of kept features below which we relax (<= 0 disables relaxation)
   * @param nominal_num_features Per-camera feature target that min_features refers to (steady state after initialization).
   * While the tracker runs with a smaller target (e.g. during initialization) min_features is scaled down proportionally.
   */
  void set_mask_gating(bool enabled, int threshold, int relaxed_threshold, int min_features, int nominal_num_features);

  /// SAVIOR (P4): upstream-compatible gating (see gating_now / mask_compat)
  void set_mask_compat(bool compat) { mask_compat = compat; }

  /**
   * @brief SAVIOR-SG: label every kept feature with the semantic class of the raw dynamic mask under it (Feature::sem_*),
   * used by the semantic chi2 gate of the updaters. KLT tracker only. Disabled by default (no effect on tracking).
   */
  void set_semantic_labels(bool enabled) { semantic_labels = enabled; }

  /**
   * @brief SAVIOR: record per-frame / per-camera feature statistics into a CSV file (KLT tracker only).
   * @param path File path to write to (parent folders are created), empty disables
   */
  void set_feature_stats_file(const std::string &path);

protected:
  /// Camera object which has all calibration in it
  std::unordered_map<size_t, std::shared_ptr<CamBase>> camera_calib;

  /// Database with all our current features
  std::shared_ptr<FeatureDatabase> database;

  /// If we are a fisheye model or not
  std::map<size_t, bool> camera_fisheye;

  /// Number of features we should try to track frame to frame
  int num_features;

  /// If we should use binocular tracking or stereo tracking for multi-camera
  bool use_stereo;

  /// What histogram equalization method we should pre-process images with?
  HistogramMethod histogram_method;

  /// Mutexs for our last set of image storage (img_last, pts_last, and ids_last)
  std::vector<std::mutex> mtx_feeds;

  /// Mutex for editing the *_last variables
  std::mutex mtx_last_vars;

  /// Last set of images (use map so all trackers render in the same order)
  std::map<size_t, cv::Mat> img_last;

  /// Last set of images (use map so all trackers render in the same order)
  std::map<size_t, cv::Mat> img_mask_last;

  /// Last set of tracked points
  std::unordered_map<size_t, std::vector<cv::KeyPoint>> pts_last;

  /// Set of IDs of each current feature in the database
  std::unordered_map<size_t, std::vector<size_t>> ids_last;

  /// Master ID for this tracker (atomic to allow for multi-threading)
  std::atomic<size_t> currid;

  // Timing variables (most children use these...)
  boost::posix_time::ptime rT1, rT2, rT3, rT4, rT5, rT6, rT7;

  // SAVIOR: dynamic mask gating ================================================

  /// Binarize a (layered) mask: 255 where mask >= threshold, 0 otherwise (threshold > 255 gives an empty mask)
  static cv::Mat threshold_mask(const cv::Mat &mask, int threshold);

  /// Copy of the message (shallow) with all masks binarized at mask_threshold if gating is enabled, else an unchanged copy.
  /// With gating: mask = max(static mask > 127, dynamic mask >= mask_threshold), i.e. the static mask keeps its upstream
  /// meaning for every threshold (also the relaxed one and the observe-only threshold 256).
  CameraData apply_mask_threshold(const CameraData &message) const;

  /// Raw layered dynamic mask of image i of the message (all zeros if the message has none)
  static cv::Mat raw_dynamic_mask(const CameraData &message, size_t i);

  /// Gating mask of image i for a given dynamic threshold: max(static > 127, dynamic >= threshold)
  static cv::Mat gating_mask(const CameraData &message, size_t i, int threshold);

  /// Returns true if the pixel under the point is rejected by a binarized mask (points outside the mask are rejected too)
  static bool is_masked(const cv::Mat &mask_bin, const cv::Point2f &pt, bool oob_masked = true) {
    int x = (int)pt.x;
    int y = (int)pt.y;
    if (x < 0 || y < 0 || x >= mask_bin.cols || y >= mask_bin.rows)
      return oob_masked;
    return mask_bin.at<uint8_t>(y, x) > 127;
  }

  /// SAVIOR (P4): gating active for the current frame (mask_gating, and with mask_compat only if a dynamic mask of this
  /// or the previous frame has a pixel >= threshold)
  bool gating_now = false;

  /// SAVIOR (P4): upstream-compatible mode (dynamic_mask_upstream_compat): frames without dynamic pixels run the exact
  /// upstream code path, out-of-bounds points are never "masked"
  bool mask_compat = false;

  /// SAVIOR (P4): any dynamic pixel >= threshold in the previous frame (any camera)
  bool dyn_any_last = false;

  /// Per-camera number of kept features below which we relax the mask (scaled if the current target is below nominal)
  int mask_relax_min_features() const {
    if (mask_nominal_num_features > 0 && num_features < mask_nominal_num_features)
      return (int)((long)mask_min_features * num_features / mask_nominal_num_features);
    return mask_min_features;
  }

  /// SAVIOR-SG: if semantic labelling is enabled
  bool semantic_labels = false;

  /// SAVIOR-SG: add the semantic label of the raw dynamic mask under each feature of this frame (no-op unless enabled)
  void update_semantic_labels(double timestamp, const std::vector<cv::KeyPoint> &pts, const std::vector<size_t> &ids,
                              const cv::Mat &mask_raw);

  /// Write one row of feature statistics (no-op if no file is open)
  void write_feature_stats(double timestamp, size_t cam_id, const std::vector<cv::KeyPoint> &pts, const std::vector<size_t> &ids,
                           size_t max_id_before, int n_rejected, bool relaxed, const cv::Mat &mask_raw);

  /// If layered mask gating is enabled
  bool mask_gating = false;

  /// Pixel value at and above which features are rejected
  int mask_threshold = 128;

  /// Pixel value at and above which features are rejected when relaxed
  int mask_relaxed_threshold = 224;

  /// Per-camera minimum number of features before relaxation
  int mask_min_features = 0;

  /// Per-camera feature target that mask_min_features refers to
  int mask_nominal_num_features = 0;

  /// Raw (non-binarized, layered) DYNAMIC masks of the current frame, used for relaxation and statistics
  std::map<size_t, cv::Mat> img_mask_raw_curr;

  /// Binarized static (upstream) masks of the current frame (> 127), never relaxed
  std::map<size_t, cv::Mat> img_mask_static_curr;

  /// Gating mask of a camera of the current frame with the relaxed threshold (static mask + dynamic core)
  cv::Mat relaxed_mask(size_t cam_id) const {
    cv::Mat mask_out;
    cv::max(img_mask_static_curr.at(cam_id), threshold_mask(img_mask_raw_curr.at(cam_id), mask_relaxed_threshold), mask_out);
    return mask_out;
  }

  /// Feature statistics file
  std::ofstream of_feature_stats;
  std::mutex mtx_feature_stats;
};

} // namespace ov_core

#endif /* OV_CORE_TRACK_BASE_H */
