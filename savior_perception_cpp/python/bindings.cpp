// SPDX-License-Identifier: GPL-3.0-or-later
// pybind11 module `savior_cpp` (offline Python <-> C++ equivalence harness and timing; not used by the node).
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <chrono>
#include <cstring>

#include <opencv2/calib3d.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/video/tracking.hpp>

#include "savior_cpp/calibration.hpp"
#include "savior_cpp/compose.hpp"
#include "savior_cpp/motion.hpp"
#include "savior_cpp/pipeline.hpp"
#include "savior_cpp/roles.hpp"
#ifdef SAVIOR_WITH_TRT
#include "savior_cpp/yolo_trt.hpp"
#endif

namespace py = pybind11;
using namespace savior;

namespace {

cv::Mat to_mat_u8(const py::array &a) {
  auto arr = py::array_t<uint8_t, py::array::c_style | py::array::forcecast>::ensure(a);
  if (!arr) throw std::invalid_argument("expected a uint8 array");
  const auto info = arr.request();
  if (info.ndim == 2) return cv::Mat((int)info.shape[0], (int)info.shape[1], CV_8U, info.ptr).clone();
  if (info.ndim == 3)
    return cv::Mat((int)info.shape[0], (int)info.shape[1], CV_8UC((int)info.shape[2]), info.ptr).clone();
  throw std::invalid_argument("expected a 2-D or 3-D image");
}

py::array_t<uint8_t> from_mat_u8(const cv::Mat &m) {
  cv::Mat c = m.isContinuous() ? m : m.clone();
  py::array_t<uint8_t> out({c.rows, c.cols});
  std::memcpy(out.mutable_data(), c.data, (size_t)c.rows * c.cols);
  return out;
}

ParamValue to_param(const py::handle &v) {
  if (py::isinstance<py::bool_>(v)) return v.cast<bool>();
  if (py::isinstance<py::int_>(v)) return (int64_t)v.cast<long long>();
  if (py::isinstance<py::float_>(v)) return v.cast<double>();
  return py::str(v).cast<std::string>();
}

py::object fnan(double v) { return std::isfinite(v) ? py::object(py::float_(v)) : py::object(py::none()); }

py::dict motion_dict(const MotionInfo &m) {
  py::dict d;
  d["id"] = m.id;
  d["state"] = m.state;
  d["l"] = m.l;
  d["obs"] = m.obs;
  if (m.has_ev) {
    d["speed"] = m.speed;
    d["q"] = m.q;
    d["n"] = m.n;
    d["rng"] = m.rng;
  }
  if (m.has_win) {
    d["w_lat"] = m.w_lat;
    d["w_slat"] = m.w_slat;
    d["w_rad"] = m.w_rad;
    d["w_srad"] = m.w_srad;
  }
  if (m.dup) d["dup"] = true;
  if (!m.sel.empty()) {
    d["sel"] = m.sel;
    d["sel_obs"] = m.sel_obs;
  }
  return d;
}

class PyPipeline {
 public:
  PyPipeline(const py::dict &flat, const std::string &roles_yaml, const std::string &calib, const std::string &cam_left,
             const std::string &cam_right, const py::object &static_mask) {
    std::vector<std::pair<std::string, ParamValue>> kv;
    for (auto it : flat) kv.emplace_back(py::str(it.first).cast<std::string>(), to_param(it.second));
    cfg_ = PipelineConfig::from_flat(kv, false);
    roles_ = RoleTable::from_yaml(roles_yaml);
    if (!calib.empty())
      rect_ = std::make_shared<StereoRectifier>(stereo_from_kalibr(calib, cam_left, cam_right, cfg_.depth.rect_focal_scale,
                                                                   cfg_.depth.rect_size_scale, cfg_.depth.rect_max_scale));
    cv::Mat sm;
    if (!static_mask.is_none()) sm = to_mat_u8(static_mask);
    pipe_ = std::make_unique<SaviorPipeline>(cfg_, roles_, rect_, sm);
  }

  // dets: list of (crop uint8 (y1-y0, x1-x0), cls, score, (x0, y0, x1, y1)); R_imu: 3x3 or None
  py::dict process(const py::array &left, const py::object &right, double stamp, const py::list &dets,
                   const py::object &R_imu) {
    const auto tc0 = std::chrono::steady_clock::now();
    cv::Mat L = to_mat_u8(left);
    cv::Mat R;
    if (!right.is_none()) R = to_mat_u8(right.cast<py::array>());
    std::vector<Instance> inst;
    for (auto d : dets) {
      auto t = d.cast<py::tuple>();
      cv::Mat crop = to_mat_u8(t[0].cast<py::array>());
      auto bb = t[3].cast<std::tuple<int, int, int, int>>();
      Box b{std::get<0>(bb), std::get<1>(bb), std::get<2>(bb), std::get<3>(bb)};
      cv::Mat m = cv::Mat::zeros(L.rows, L.cols, CV_8U);
      cv::Mat c01 = crop != 0;
      c01 /= 255;
      c01.copyTo(m(b.rect()));
      inst.emplace_back(m, t[1].cast<std::string>(), t[2].cast<double>(), &b);
    }
    std::optional<Mat3> Ri;
    if (!R_imu.is_none()) {
      auto a = py::array_t<double, py::array::c_style | py::array::forcecast>::ensure(R_imu);
      Mat3 M;
      for (int r = 0; r < 3; ++r)
        for (int k = 0; k < 3; ++k) M(r, k) = a.at(r, k);
      Ri = M;
    }
    const auto tc1 = std::chrono::steady_clock::now();
    const FrameResult &res = pipe_->process(L, R.empty() ? nullptr : &R, stamp, std::move(inst), Ri);
    const auto tc2 = std::chrono::steady_clock::now();
    py::dict out;
    out["mask_left"] = from_mat_u8(res.mask_left);
    out["mask_right"] = from_mat_u8(res.mask_right);
    py::list li;
    for (size_t k = 0; k < res.instances.size(); ++k) {
      const Instance &x = res.instances[k];
      py::dict d;
      d["cls"] = x.cls;
      d["role"] = role_name(x.role);
      d["status"] = status_name(x.status);
      d["bbox"] = py::make_tuple(x.bbox.x0, x.bbox.y0, x.bbox.x1, x.bbox.y1);
      d["disparity"] = fnan(x.disparity);
      d["depth"] = fnan(x.depth);
      d["sigma_z"] = fnan(x.sigma_z);
      d["n_depth_px"] = x.n_depth_px;
      d["parent"] = x.parent;
      d["track_id"] = x.track_id;
      d["motion"] = x.motion ? py::object(motion_dict(*x.motion)) : py::object(py::none());
      d["carried"] = (int)k >= res.n_detections;
      li.append(d);
    }
    out["instances"] = li;
    py::list links;
    for (auto &l : res.links) links.append(py::make_tuple(l.first, l.second));
    out["links"] = links;
    py::dict tm;
    for (auto &kv : res.timings_ms) tm[kv.first.c_str()] = kv.second;
    tm["convert_in"] = std::chrono::duration<double, std::milli>(tc1 - tc0).count();
    tm["process_call"] = std::chrono::duration<double, std::milli>(tc2 - tc1).count();
    if (res.has_motion) {
      tm["m_flow_ego"] = res.motion.ms_flow_ego;
      tm["m_assoc"] = res.motion.ms_assoc;
      tm["m_points"] = res.motion.ms_points;
    }
    out["timings"] = tm;
    py::dict ms;
    if (res.has_motion) {
      ms["n_bg"] = res.motion.n_bg;
      ms["n_inl"] = res.motion.n_inl;
      ms["t_ok"] = res.motion.t_ok;
      ms["n_tracks"] = res.motion.n_tracks;
      ms["n_inst_pts"] = res.motion.n_inst_pts;
      if (res.motion.has_ego) {
        ms["sigma_bg_px"] = res.motion.sigma_bg_px;
        ms["t"] = py::make_tuple(res.motion.t[0], res.motion.t[1], res.motion.t[2]);
        ms["dtheta_deg"] = res.motion.dtheta_deg;
        ms["rot_deg"] = res.motion.rot_deg;
      }
    }
    out["motion"] = ms;
    py::dict ss;
    if (res.has_selective) {
      ss["converged"] = res.selective.converged;
      ss["onset_t"] = res.selective.onset_t ? py::object(py::float_(*res.selective.onset_t)) : py::object(py::none());
      ss["n_static"] = res.selective.n_static;
      ss["n_labels"] = res.selective.n_labels;
      ss["n_held"] = res.selective.n_held;
    }
    out["selective"] = ss;
    out["depth_info"] = py::make_tuple(res.depth_info.n_rois, res.depth_info.matched_px);
    out["n_tracks"] = res.n_tracks;
    out["tracks"] = res.tracks_summary;
    out["core_px"] = res.core_px;
    out["ext_px"] = res.ext_px;
    return out;
  }
  std::string stats_json(bool compact) const { return pipe_->stats_json(compact); }
  py::tuple debug_points() const {
    const MotionEstimator *m = pipe_->motion();
    if (!m) return py::make_tuple();
    auto pts = [](const std::vector<cv::Point2d> &p) {
      py::array_t<double> a({(py::ssize_t)p.size(), (py::ssize_t)2});
      for (size_t i = 0; i < p.size(); ++i) { a.mutable_at(i, 0) = p[i].x; a.mutable_at(i, 1) = p[i].y; }
      return a;
    };
    return py::make_tuple(pts(m->inst_points()), m->inst_point_tracks(), pts(m->bg_points()));
  }
  py::dict rect_info() const {
    py::dict d;
    if (rect_) {
      d["f"] = rect_->f;
      d["baseline"] = rect_->baseline;
      d["cx"] = rect_->cx;
      d["cy"] = rect_->cy;
      d["rect_size"] = py::make_tuple(rect_->rect_w, rect_->rect_h);
      for (int i = 0; i < 2; ++i) {
        py::array_t<double> R({3, 3});
        for (int r = 0; r < 3; ++r)
          for (int c = 0; c < 3; ++c) R.mutable_at(r, c) = rect_->R_rect[i](r, c);
        d[("R_rect" + std::to_string(i)).c_str()] = R;
        auto f32 = [](const cv::Mat &m) {
          py::array_t<float> a({m.rows, m.cols});
          std::memcpy(a.mutable_data(), m.data, m.total() * 4);
          return a;
        };
        d[("raw_to_rect_x" + std::to_string(i)).c_str()] = f32(rect_->raw_to_rect_x[i]);
        d[("raw_to_rect_y" + std::to_string(i)).c_str()] = f32(rect_->raw_to_rect_y[i]);
        d[("rect_to_raw_x" + std::to_string(i)).c_str()] = f32(rect_->rect_to_raw_x[i]);
        d[("rect_to_raw_y" + std::to_string(i)).c_str()] = f32(rect_->rect_to_raw_y[i]);
      }
    }
    return d;
  }

 private:
  PipelineConfig cfg_;
  RoleTable roles_;
  std::shared_ptr<StereoRectifier> rect_;
  std::unique_ptr<SaviorPipeline> pipe_;
};

#ifdef SAVIOR_WITH_TRT
class PyYolo {
 public:
  PyYolo(const std::string &engine, double conf, double iou, const std::vector<std::string> &classes) {
    YoloOptions o;
    o.engine_path = engine;
    o.conf = conf;
    o.iou = iou;
    o.classes = classes;
    seg_ = std::make_unique<YoloTrtSegmenter>(o);
  }
  // -> list of (crop uint8 0/1, cls, score, (x0, y0, x1, y1))
  py::list predict(const py::array &img) {
    cv::Mat m = to_mat_u8(img);
    auto inst = seg_->predict(m);
    py::list out;
    for (auto &x : inst) out.append(py::make_tuple(from_mat_u8(x.crop()), x.cls, x.score,
                                                   py::make_tuple(x.bbox.x0, x.bbox.y0, x.bbox.x1, x.bbox.y1)));
    return out;
  }
  py::dict timings() const {
    const auto &t = seg_->last_timings();
    py::dict d;
    d["pre"] = t.pre;
    d["infer"] = t.infer;
    d["nms"] = t.nms;
    d["masks"] = t.masks;
    d["total"] = t.total;
    return d;
  }
  void warmup(int h, int w) { seg_->warmup(h, w); }

 private:
  std::unique_ptr<YoloTrtSegmenter> seg_;
};
#endif

// C++ gyro integration of a sample stream, rotations between consecutive frame stamps (node-path check)
std::vector<py::object> gyro_rotations(const std::vector<double> &t, const std::vector<std::array<double, 3>> &w,
                                       const std::vector<double> &frames, double max_age) {
  GyroIntegrator g(max_age);
  for (size_t i = 0; i < t.size(); ++i) g.add(t[i], Vec3(w[i][0], w[i][1], w[i][2]));
  std::vector<py::object> out;
  for (size_t k = 0; k < frames.size(); ++k) {
    if (k == 0) {
      out.push_back(py::none());
      continue;
    }
    auto R = g.rotation(frames[k - 1], frames[k]);
    if (!R) {
      out.push_back(py::none());
      continue;
    }
    py::array_t<double> a({3, 3});
    for (int r = 0; r < 3; ++r)
      for (int c = 0; c < 3; ++c) a.mutable_at(r, c) = (*R)(r, c);
    out.push_back(a);
  }
  return out;
}

#include "cvops.inc"

}  // namespace

PYBIND11_MODULE(savior_cpp, m) {
  m.doc() = "SAVIOR perception C++ port (offline harness bindings)";
  py::class_<PyPipeline>(m, "Pipeline")
      .def(py::init<const py::dict &, const std::string &, const std::string &, const std::string &,
                    const std::string &, const py::object &>(),
           py::arg("config"), py::arg("roles_file"), py::arg("calib_file"), py::arg("cam_left") = "cam0",
           py::arg("cam_right") = "cam1", py::arg("static_mask") = py::none())
      .def("process", &PyPipeline::process, py::arg("left"), py::arg("right"), py::arg("stamp"), py::arg("dets"),
           py::arg("R_imu") = py::none())
      .def("stats_json", &PyPipeline::stats_json, py::arg("compact") = false)
      .def("debug_points", &PyPipeline::debug_points)
      .def("rect_info", &PyPipeline::rect_info);
#ifdef SAVIOR_WITH_TRT
  py::class_<PyYolo>(m, "Yolo")
      .def(py::init<const std::string &, double, double, const std::vector<std::string> &>(), py::arg("engine"),
           py::arg("conf") = 0.25, py::arg("iou") = 0.7, py::arg("classes") = std::vector<std::string>())
      .def("predict", &PyYolo::predict)
      .def("timings", &PyYolo::timings)
      .def("warmup", &PyYolo::warmup);
#endif
  m.def("gyro_rotations", &gyro_rotations, py::arg("t"), py::arg("w"), py::arg("frames"), py::arg("max_age") = 1e9);
  m.def("set_num_threads", [](int n) { cv::setNumThreads(n); });
  m.def("get_num_threads", []() { return cv::getNumThreads(); });
  auto cvm = m.def_submodule("cvops", "OpenCV primitives as called by the pipeline (version analysis)");
  cvm.def("resize_area", &cvops::resize_area);
  cvm.def("gftt", &cvops::gftt);
  cvm.def("lk", &cvops::lk);
  cvm.def("sgbm", &cvops::sgbm);
  cvm.def("remap_lin", &cvops::remap_lin);
  cvm.def("contours", &cvops::contours);
  cvm.def("fillpoly", &cvops::fillpoly);
  cvm.def("fillpoly411", &cvops::fillpoly411);
  cvm.def("erode3", &cvops::erode3);
  cvm.def("dilate_ell", &cvops::dilate_ell);
  cvm.def("undistort", &cvops::undistort);
  cvm.def("project", &cvops::project);
  cvm.def("resize_nearest", &cvops::resize_nearest);
  cvm.def("moments", &cvops::moments);
  cvm.def("circles", &cvops::circles);
  cvm.def("lk_init", &cvops::lk_init);
  cvm.def("erode_k", &cvops::erode_k);
  m.attr("opencv_version") = CV_VERSION;
}
