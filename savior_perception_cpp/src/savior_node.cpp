// SPDX-License-Identifier: GPL-3.0-or-later
// savior_node (C++): composable rclcpp component, drop-in replacement of savior_perception/node.py.
// Contract (docs/INTERFACE.md 3.1): /savior/mask/left|right mono8, raw size, 0/192/255, header.stamp ==
// left image stamp (both masks), RELIABLE KEEP_LAST 10; exactly one mask pair per exact-time-synced stereo frame (zeros
// on failure). Same parameters (node + "<section>.<field>" pipeline keys) and topics as the Python node. Masks and stats
// are published as unique_ptr messages: zero-copy intra-process delivery when composed with OpenVINS in one container
// with use_intra_process_comms.
#include <chrono>
#include <deque>
#include <map>
#include <memory>
#include <optional>
#include <string>

#include <ament_index_cpp/get_package_share_directory.hpp>
#include <message_filters/subscriber.h>
#include <message_filters/time_synchronizer.h>
#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_components/register_node_macro.hpp>
#include <sensor_msgs/msg/image.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <std_msgs/msg/string.hpp>

#include "savior_cpp/json.hpp"
#include "savior_cpp/pipeline.hpp"
#ifdef SAVIOR_WITH_TRT
#include "savior_cpp/yolo_trt.hpp"
#endif

namespace savior_perception_cpp {

using sensor_msgs::msg::Image;
using sensor_msgs::msg::Imu;
using namespace savior;
using WallClock = std::chrono::steady_clock;

namespace {

double wall_s() { return std::chrono::duration<double>(WallClock::now().time_since_epoch()).count(); }

// sensor_msgs/Image -> cv::Mat (uint8 gray or BGR), same conversions as node.image_to_numpy
cv::Mat image_to_mat(const Image &msg) {
  const std::string &enc = msg.encoding;
  int ch;
  bool is16 = false;
  if (enc == "mono8" || enc == "8UC1") ch = 1;
  else if (enc == "bgr8" || enc == "rgb8" || enc == "8UC3") ch = 3;
  else if (enc == "bgra8" || enc == "rgba8") ch = 4;
  else if (enc == "mono16" || enc == "16UC1") { ch = 1; is16 = true; }
  else throw std::invalid_argument("unsupported image encoding '" + enc + "'");
  const int h = (int)msg.height, w = (int)msg.width;
  if (is16) {
    cv::Mat out(h, w, CV_8U);
    for (int y = 0; y < h; ++y) {
      const uint8_t *r = msg.data.data() + (size_t)y * msg.step;
      for (int x = 0; x < w; ++x) {
        const uint16_t v = msg.is_bigendian ? (uint16_t)((r[2 * x] << 8) | r[2 * x + 1]) : (uint16_t)(r[2 * x] | (r[2 * x + 1] << 8));
        out.at<uint8_t>(y, x) = (uint8_t)(v >> 8);
      }
    }
    return out;
  }
  cv::Mat view(h, w, CV_8UC(ch), (void *)msg.data.data(), msg.step);
  cv::Mat out;
  if (enc == "rgb8") cv::cvtColor(view, out, cv::COLOR_RGB2BGR);
  else if (enc == "rgba8") cv::cvtColor(view, out, cv::COLOR_RGBA2BGR);
  else if (enc == "bgra8") cv::cvtColor(view, out, cv::COLOR_BGRA2BGR);
  else out = view.clone();
  return out;
}

std::unique_ptr<Image> mat_to_image(const cv::Mat &m, const builtin_interfaces::msg::Time &stamp,
                                    const std::string &frame_id) {
  auto msg = std::make_unique<Image>();
  msg->header.stamp = stamp;
  msg->header.frame_id = frame_id;
  msg->height = m.rows;
  msg->width = m.cols;
  msg->encoding = "mono8";
  msg->is_bigendian = 0;
  msg->step = m.cols;
  msg->data.resize((size_t)m.rows * m.cols);
  if (m.isContinuous()) std::memcpy(msg->data.data(), m.data, msg->data.size());
  else
    for (int y = 0; y < m.rows; ++y) std::memcpy(msg->data.data() + (size_t)y * m.cols, m.ptr(y), m.cols);
  return msg;
}

ParamValue to_value(const rclcpp::Parameter &p) {
  switch (p.get_type()) {
    case rclcpp::ParameterType::PARAMETER_BOOL: return p.as_bool();
    case rclcpp::ParameterType::PARAMETER_INTEGER: return (int64_t)p.as_int();
    case rclcpp::ParameterType::PARAMETER_DOUBLE: return p.as_double();
    case rclcpp::ParameterType::PARAMETER_STRING: return p.as_string();
    default: return p.value_to_string();
  }
}

rclcpp::ParameterValue to_rcl(const ParamValue &v) {
  if (std::holds_alternative<bool>(v)) return rclcpp::ParameterValue(std::get<bool>(v));
  if (std::holds_alternative<int64_t>(v)) return rclcpp::ParameterValue(std::get<int64_t>(v));
  if (std::holds_alternative<double>(v)) return rclcpp::ParameterValue(std::get<double>(v));
  return rclcpp::ParameterValue(std::get<std::string>(v));
}

}  // namespace

class SaviorNode : public rclcpp::Node {
 public:
  explicit SaviorNode(const rclcpp::NodeOptions &options) : rclcpp::Node("savior_node", options) {
    declare_all();
    const int nt = (int)P_int("num_threads");
    if (nt > 0) {
      cv::setNumThreads(nt);
      RCLCPP_INFO(get_logger(), "num_threads=%d (cv)", nt);
    }
    std::vector<std::pair<std::string, ParamValue>> flat;
    for (auto &kv : PipelineConfig().to_flat()) flat.emplace_back(kv.first, to_value(get_parameter(kv.first)));
    cfg_ = PipelineConfig::from_flat(flat);
    std::string roles_file = P_str("roles_file");
    if (roles_file.empty())
      roles_file = ament_index_cpp::get_package_share_directory("savior_perception_cpp") + "/config/roles_default.yaml";
    roles_ = RoleTable::from_yaml(roles_file);
    RCLCPP_INFO(get_logger(), "roles from %s: %s", roles_file.c_str(), roles_.repr().c_str());
    if (!P_str("calib_file").empty()) {
      rect_ = std::make_shared<StereoRectifier>(stereo_from_kalibr(P_str("calib_file"), P_str("cam_left"),
                                                                   P_str("cam_right"), cfg_.depth.rect_focal_scale,
                                                                   cfg_.depth.rect_size_scale, cfg_.depth.rect_max_scale));
      RCLCPP_INFO(get_logger(), "stereo calib %s: f=%.1fpx b=%.4fm rect=(%d, %d) models=(%s,%s)",
                  P_str("calib_file").c_str(), rect_->f, rect_->baseline, rect_->rect_w, rect_->rect_h,
                  rect_->cams[0].model.c_str(), rect_->cams[1].model.c_str());
    } else {
      RCLCPP_WARN(get_logger(), "no calib_file: stereo depth, depth-guided extension and right-mask warp disabled "
                                "(right mask is all zeros)");
    }
    backend_ = P_str("segmenter.backend");
    std::transform(backend_.begin(), backend_.end(), backend_.begin(), ::tolower);
    if (backend_.empty()) backend_ = "none";
    if (backend_ == "yolo") {
#ifdef SAVIOR_WITH_TRT
      YoloOptions o;
      o.engine_path = P_str("segmenter.model");
      if (o.engine_path.size() < 7 || o.engine_path.substr(o.engine_path.size() - 7) != ".engine")
        throw std::invalid_argument("segmenter.model must be a TensorRT .engine (Ultralytics export) for the C++ node");
      o.conf = P_dbl("segmenter.conf");
      o.iou = P_dbl("segmenter.iou");
      o.retina_masks = get_parameter("segmenter.retina_masks").as_bool();
      if (get_parameter("segmenter.filter_classes").as_bool()) o.classes = roles_.relevant_classes();
      yolo_ = std::make_unique<YoloTrtSegmenter>(o);
#else
      throw std::invalid_argument("savior_perception_cpp was built without TensorRT (segmenter.backend yolo unavailable)");
#endif
    } else if (backend_ != "none") {
      throw std::invalid_argument("segmenter.backend '" + backend_ + "': the C++ node implements yolo | none "
                                  "(oracle backends: use the Python savior_node)");
    }
    warmed_ = !get_parameter("segmenter.warmup").as_bool();
    if (!warmed_ && rect_) warmup(rect_->cams[0].height, rect_->cams[0].width);
    rclcpp::QoS qos = rclcpp::QoS(rclcpp::KeepLast(10)).reliable();
    pub_left_ = create_publisher<Image>(P_str("mask_left_topic"), qos);
    pub_right_ = create_publisher<Image>(P_str("mask_right_topic"), qos);
    pub_stats_ = create_publisher<std_msgs::msg::String>(P_str("stats_topic"), qos);
    if (cfg_.motion.enable) {
      if (P_str("imu_topic").empty()) throw std::invalid_argument("motion.enable requires imu_topic");
      gyro_ = std::make_unique<GyroIntegrator>();
      auto iqos = rclcpp::QoS(rclcpp::KeepLast((size_t)P_int("imu_queue_size"))).reliable();
      imu_sub_ = create_subscription<Imu>(P_str("imu_topic"), iqos, [this](Imu::ConstSharedPtr m) { on_imu(m); });
      flush_timer_ = create_wall_timer(std::chrono::milliseconds(5), [this]() { flush(); });
      RCLCPP_INFO(get_logger(), "motion evidence on: gyro from %s (wait <= %ld ms)", P_str("imu_topic").c_str(),
                  (long)P_int("imu_wait_ms"));
    }
    rmw_qos_profile_t rq = rmw_qos_profile_default;
    rq.reliability = RMW_QOS_POLICY_RELIABILITY_RELIABLE;
    rq.history = RMW_QOS_POLICY_HISTORY_KEEP_LAST;
    rq.depth = 10;
    sub_l_.subscribe(this, P_str("left_topic"), rq);
    sub_r_.subscribe(this, P_str("right_topic"), rq);
    sync_ = std::make_unique<message_filters::TimeSynchronizer<Image, Image>>(sub_l_, sub_r_,
                                                                              (uint32_t)P_int("sync_queue_size"));
    sync_->registerCallback(std::bind(&SaviorNode::on_images, this, std::placeholders::_1, std::placeholders::_2));
    t_log_ = wall_s();
    last_imu_wall_ = wall_s();
    RCLCPP_INFO(get_logger(), "savior_node up: backend=%s left=%s right=%s -> %s, %s (C++ savior_perception_cpp)",
                backend_.c_str(), P_str("left_topic").c_str(), P_str("right_topic").c_str(),
                P_str("mask_left_topic").c_str(), P_str("mask_right_topic").c_str());
  }

 private:
  // ------------------------------------------------------------------ parameters (params.py NODE_DEFAULTS + config)
  void declare_all() {
    rcl_interfaces::msg::ParameterDescriptor dyn;
    dyn.dynamic_typing = true;
    const std::vector<std::pair<std::string, ParamValue>> node_defaults = {
        {"left_topic", std::string("/cam0/image_raw")}, {"right_topic", std::string("/cam1/image_raw")},
        {"seg_topic", std::string("")}, {"seg_right_topic", std::string("")},
        {"mask_left_topic", std::string("/savior/mask/left")}, {"mask_right_topic", std::string("/savior/mask/right")},
        {"debug_topic", std::string("/savior/debug/overlay")}, {"stats_topic", std::string("/savior/stats")},
        {"publish_debug", false}, {"sync_queue_size", (int64_t)30}, {"frame_id_left", std::string("")},
        {"frame_id_right", std::string("")}, {"calib_file", std::string("")}, {"cam_left", std::string("cam0")},
        {"cam_right", std::string("cam1")}, {"roles_file", std::string("")},
        {"segmenter.backend", std::string("none")}, {"segmenter.model", std::string("")}, {"segmenter.conf", 0.25},
        {"segmenter.iou", 0.7}, {"segmenter.imgsz", (int64_t)640}, {"segmenter.device", std::string("")},
        {"segmenter.half", false}, {"segmenter.retina_masks", true}, {"segmenter.filter_classes", true},
        {"segmenter.colormap_file", std::string("")}, {"segmenter.warmup", true}, {"segmenter.fast_masks", false},
        {"stats_compact", false}, {"num_threads", (int64_t)4}, {"imu_topic", std::string("")},
        {"imu_wait_ms", (int64_t)300}, {"imu_queue_size", (int64_t)2000}};
    for (auto &kv : node_defaults) declare_parameter(kv.first, to_rcl(kv.second), dyn);
    for (auto &kv : PipelineConfig().to_flat()) declare_parameter(kv.first, to_rcl(kv.second), dyn);
  }
  std::string P_str(const std::string &k) { return param_to_string(to_value(get_parameter(k))); }
  int64_t P_int(const std::string &k) {
    auto v = to_value(get_parameter(k));
    if (std::holds_alternative<int64_t>(v)) return std::get<int64_t>(v);
    if (std::holds_alternative<double>(v)) return (int64_t)std::get<double>(v);
    return std::stoll(param_to_string(v));
  }
  double P_dbl(const std::string &k) {
    auto v = to_value(get_parameter(k));
    if (std::holds_alternative<double>(v)) return std::get<double>(v);
    if (std::holds_alternative<int64_t>(v)) return (double)std::get<int64_t>(v);
    return std::stod(param_to_string(v));
  }

  void warmup(int h, int w) {
    warmed_ = true;
#ifdef SAVIOR_WITH_TRT
    if (!yolo_) return;
    try {
      const auto t0 = WallClock::now();
      yolo_->warmup(h, w);
      RCLCPP_INFO(get_logger(), "segmenter warmup %dx%d: %.0f ms", w, h,
                  std::chrono::duration<double, std::milli>(WallClock::now() - t0).count());
    } catch (const std::exception &e) {
      RCLCPP_WARN(get_logger(), "segmenter warmup failed: %s", e.what());
    }
#else
    (void)h;
    (void)w;
#endif
  }

  // ------------------------------------------------------------------ IMU (P4)
  void on_imu(const Imu::ConstSharedPtr &msg) {
    const double t = msg->header.stamp.sec + msg->header.stamp.nanosec * 1e-9;
    gyro_->add(t, Vec3(msg->angular_velocity.x, msg->angular_velocity.y, msg->angular_velocity.z));
    last_imu_wall_ = wall_s();
    flush();
  }

  void flush() {
    const double off = cfg_.motion.imu_time_offset_s;
    const double wait = (double)P_int_cached_wait() * 1e-3;
    while (!pending_.empty()) {
      auto &pd = pending_.front();
      const double t_img = pd.left->header.stamp.sec + pd.left->header.stamp.nanosec * 1e-9;
      const bool covered = gyro_->last_time() >= t_img + off;
      const double now = wall_s();
      const bool timed_out = (now - pd.arrival) > wait && (now - last_imu_wall_) > wait;
      if (!(covered || timed_out)) return;
      Pending p = pd;
      pending_.pop_front();
      if (!covered) {
        imu_timeouts_ += 1;
        RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000, "no gyro up to t=%.3f after %.0f ms (%d timeouts)", t_img,
                             wait * 1e3, imu_timeouts_);
      }
      std::optional<Mat3> R;
      if (prev_img_t_) R = gyro_->rotation(*prev_img_t_ + off, t_img + off);
      prev_img_t_ = t_img;
      JsonWriter j;
      j.begin_obj().key("covered").val(covered).key("timeouts").val(imu_timeouts_);
      j.key("wait_ms").val(round_ndigits((wall_s() - p.arrival) * 1e3, 2)).end_obj();
      run(p.left, p.right, R, j.str());
    }
  }
  int64_t P_int_cached_wait() {
    if (imu_wait_ms_ < 0) imu_wait_ms_ = P_int("imu_wait_ms");
    return imu_wait_ms_;
  }

  void on_images(const Image::ConstSharedPtr &l, const Image::ConstSharedPtr &r) {
    if (gyro_) {
      pending_.push_back({l, r, wall_s()});
      flush();
      return;
    }
    run(l, r, std::nullopt, "");
  }

  void publish_masks(const Image &l, const Image &r, const cv::Mat &ml, const cv::Mat &mr) {
    const std::string fl = P_cached("frame_id_left"), fr = P_cached("frame_id_right");
    pub_left_->publish(mat_to_image(ml, l.header.stamp, fl.empty() ? l.header.frame_id : fl));
    pub_right_->publish(mat_to_image(mr, l.header.stamp, fr.empty() ? r.header.frame_id : fr));
  }
  std::string P_cached(const std::string &k) {
    auto it = pcache_.find(k);
    if (it != pcache_.end()) return it->second;
    return pcache_[k] = P_str(k);
  }

  void run(const Image::ConstSharedPtr &l, const Image::ConstSharedPtr &r, const std::optional<Mat3> &R_imu,
           const std::string &imu_json) {
    try {
      process(*l, *r, R_imu, imu_json);
    } catch (const std::exception &e) {
      n_fail_ += 1;
      RCLCPP_ERROR_THROTTLE(get_logger(), *get_clock(), 5000,
                            "frame processing failed (%d so far), publishing empty masks: %s", n_fail_, e.what());
      publish_masks(*l, *r, cv::Mat::zeros(l->height, l->width, CV_8U), cv::Mat::zeros(r->height, r->width, CV_8U));
    }
  }

  void process(const Image &lm, const Image &rm, const std::optional<Mat3> &R_imu, const std::string &imu_json) {
    const auto t0 = WallClock::now();
    cv::Mat left = image_to_mat(lm), right = image_to_mat(rm);
    if (!pipeline_) build_pipeline(left, right);
    if (!warmed_) warmup(left.rows, left.cols);
    const auto t1 = WallClock::now();
    std::vector<Instance> instances;
#ifdef SAVIOR_WITH_TRT
    if (yolo_) instances = yolo_->predict(left);
#endif
    const auto t2 = WallClock::now();
    const double stamp_f = lm.header.stamp.sec + lm.header.stamp.nanosec * 1e-9;
    const FrameResult &res = pipeline_->process(left, &right, stamp_f, std::move(instances), gyro_ ? R_imu : std::nullopt);
    cv::Mat mr = res.mask_right;
    if (mr.rows != (int)rm.height || mr.cols != (int)rm.width) mr = cv::Mat::zeros(rm.height, rm.width, CV_8U);
    publish_masks(lm, rm, res.mask_left, mr);
    const auto t3 = WallClock::now();
    auto msd = [](WallClock::time_point a, WallClock::time_point b) {
      return round_ndigits(std::chrono::duration<double, std::milli>(b - a).count(), 3);
    };
    JsonWriter tj;
    tj.key("convert").val(msd(t0, t1)).key("segment").val(msd(t1, t2)).key("node_total").val(msd(t0, t3));
    JsonWriter sj;
    sj.begin_obj().key("sec").val((long)lm.header.stamp.sec).key("nanosec").val((long)lm.header.stamp.nanosec);
    sj.key("t").val(stamp_f).end_obj();
    std::string top;
    if (gyro_) top = "\"imu\": " + (imu_json.empty() ? std::string("null") : imu_json);
    // tj starts with a separator-less key list: strip nothing, JsonWriter emits `"convert": ...` pairs
    auto msg = std::make_unique<std_msgs::msg::String>();
    msg->data = pipeline_->stats_json(compact_, tj.str(), sj.str(), top);
    pub_stats_->publish(std::move(msg));
    log_timing(res, msd(t0, t1), msd(t1, t2), msd(t0, t3));
  }

  void build_pipeline(const cv::Mat &left, const cv::Mat &right) {
    std::shared_ptr<const StereoRectifier> rect = rect_;
    if (rect && (rect->cams[0].width != left.cols || rect->cams[0].height != left.rows ||
                 rect->cams[1].width != right.cols || rect->cams[1].height != right.rows)) {
      RCLCPP_ERROR(get_logger(), "image sizes != calibration: disabling stereo depth and right-mask warp");
      rect.reset();
    }
    cv::Mat static_mask;
    if (cfg_.motion.enable && !cfg_.motion.static_mask_file.empty()) {
      cv::Mat sm = cv::imread(cfg_.motion.static_mask_file, cv::IMREAD_UNCHANGED);
      if (!sm.empty() && sm.channels() >= 3) {
        std::vector<cv::Mat> chs;
        cv::split(sm, chs);
        cv::Mat mx = cv::max(chs[0], chs[1]);
        static_mask = cv::max(mx, chs[2]);
      } else {
        static_mask = sm;
      }
      if (static_mask.empty() || static_mask.rows != left.rows || static_mask.cols != left.cols) {
        RCLCPP_WARN(get_logger(), "motion.static_mask_file %s unusable, ignored", cfg_.motion.static_mask_file.c_str());
        static_mask = cv::Mat();
      }
    }
    compact_ = get_parameter("stats_compact").as_bool();
    pipeline_ = std::make_unique<SaviorPipeline>(cfg_, roles_, rect, static_mask);
  }

  void log_timing(const FrameResult &res, double convert, double segment, double total) {
    n_ += 1;
    for (auto &kv : res.timings_ms) acc_[kv.first] += kv.second;
    acc_["convert"] += convert;
    acc_["segment"] += segment;
    acc_["node_total"] += total;
    const double now = wall_s();
    if (now - t_log_ >= 10.0) {
      std::string s;
      char b[64];
      for (auto &kv : acc_) {
        std::snprintf(b, sizeof(b), "%s=%.1f ", kv.first.c_str(), kv.second / std::max(1, n_));
        s += b;
      }
      RCLCPP_INFO(get_logger(), "%d frames, mean ms: %s", n_, s.c_str());
      n_ = 0;
      acc_.clear();
      t_log_ = now;
    }
  }

  struct Pending {
    Image::ConstSharedPtr left, right;
    double arrival;
  };
  PipelineConfig cfg_;
  RoleTable roles_;
  std::shared_ptr<StereoRectifier> rect_;
  std::string backend_;
#ifdef SAVIOR_WITH_TRT
  std::unique_ptr<YoloTrtSegmenter> yolo_;
#endif
  std::unique_ptr<SaviorPipeline> pipeline_;
  bool warmed_ = false, compact_ = false;
  rclcpp::Publisher<Image>::SharedPtr pub_left_, pub_right_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pub_stats_;
  rclcpp::Subscription<Imu>::SharedPtr imu_sub_;
  rclcpp::TimerBase::SharedPtr flush_timer_;
  message_filters::Subscriber<Image> sub_l_, sub_r_;
  std::unique_ptr<message_filters::TimeSynchronizer<Image, Image>> sync_;
  std::unique_ptr<GyroIntegrator> gyro_;
  std::deque<Pending> pending_;
  std::optional<double> prev_img_t_;
  int imu_timeouts_ = 0, n_fail_ = 0, n_ = 0;
  int64_t imu_wait_ms_ = -1;
  double last_imu_wall_ = 0, t_log_ = 0;
  std::map<std::string, double> acc_;
  std::map<std::string, std::string> pcache_;
};

}  // namespace savior_perception_cpp

RCLCPP_COMPONENTS_REGISTER_NODE(savior_perception_cpp::SaviorNode)
