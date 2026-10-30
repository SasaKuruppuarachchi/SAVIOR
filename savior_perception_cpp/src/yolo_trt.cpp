// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/yolo_trt.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <numeric>
#include <regex>
#include <array>
#include <set>
#include <stdexcept>

#include <NvInfer.h>
#include <cuda_runtime.h>
#include <opencv2/imgproc.hpp>

#include "savior_cpp/roles.hpp"

namespace savior_cuda {
void launch_preprocess(const uint8_t *src, int sh, int sw, int sc, int sstep, float *dst, int H, int W, int top, int left,
                       const float *lut, cudaStream_t st);
void launch_logits(const float *coef, const float *proto, float *logits, int N, int nm, int P, cudaStream_t st);
void launch_upsample(const float *in, float *out, int N, int H, int W, int f, cudaStream_t st);
void launch_masks(const float *logits, int Hs, int Ws, int top, int left, int ih, int iw, int oh, int ow, int resize,
                  const float *fbox, const int *ibox, const long long *offs, uint8_t *out, int N, cudaStream_t st);
}  // namespace savior_cuda

namespace savior {
namespace {

#define CUDA_CHECK(x)                                                                         \
  do {                                                                                        \
    cudaError_t e_ = (x);                                                                     \
    if (e_ != cudaSuccess) throw std::runtime_error(std::string("CUDA: ") + cudaGetErrorString(e_)); \
  } while (0)

class TrtLogger : public nvinfer1::ILogger {
 public:
  void log(Severity s, const char *msg) noexcept override {
    if (s <= Severity::kWARNING) std::fprintf(stderr, "[TensorRT] %s\n", msg);
  }
};
TrtLogger g_logger;

using Clock = std::chrono::steady_clock;
double ms(Clock::time_point a, Clock::time_point b) { return std::chrono::duration<double, std::milli>(b - a).count(); }

struct DevBuf {
  void *p = nullptr;
  size_t n = 0;
  void reserve(size_t bytes) {
    if (bytes <= n) return;
    if (p) cudaFree(p);
    CUDA_CHECK(cudaMalloc(&p, bytes));
    n = bytes;
  }
  ~DevBuf() {
    if (p) cudaFree(p);
  }
};

}  // namespace

struct YoloTrtSegmenter::Impl {
  std::unique_ptr<nvinfer1::IRuntime> runtime;
  std::unique_ptr<nvinfer1::ICudaEngine> engine;
  std::unique_ptr<nvinfer1::IExecutionContext> ctx;
  cudaStream_t stream = nullptr;
  std::string in_name, out0_name, out1_name;
  DevBuf d_in, d_out0, d_out1, d_src, d_lut, d_coef, d_logits, d_up, d_fbox, d_ibox, d_offs, d_masks;
  std::vector<float> h_out0;
  std::vector<uint8_t> h_masks;
  ~Impl() {
    ctx.reset();
    engine.reset();
    runtime.reset();
    if (stream) cudaStreamDestroy(stream);
  }
};

static void parse_meta(const std::string &js, std::map<int, std::string> &names, int &h, int &w) {
  const auto p = js.find("\"names\"");
  if (p != std::string::npos) {
    const auto a = js.find('{', p), b = js.find('}', a);
    const std::string body = js.substr(a + 1, b - a - 1);
    std::regex re("\"([0-9]+)\"\\s*:\\s*\"([^\"]*)\"");
    for (auto it = std::sregex_iterator(body.begin(), body.end(), re); it != std::sregex_iterator(); ++it)
      names[std::stoi((*it)[1])] = (*it)[2];
  }
  std::smatch m;
  if (std::regex_search(js, m, std::regex("\"imgsz\"\\s*:\\s*\\[\\s*([0-9]+)\\s*,\\s*([0-9]+)\\s*\\]"))) {
    h = std::stoi(m[1]);
    w = std::stoi(m[2]);
  }
}

YoloTrtSegmenter::YoloTrtSegmenter(const YoloOptions &opt) : impl_(new Impl), opt_(opt) {
  if (!opt.retina_masks) throw std::invalid_argument("YoloTrtSegmenter: only retina_masks=true is implemented");
  std::ifstream f(opt.engine_path, std::ios::binary);
  if (!f) throw std::runtime_error("cannot open engine " + opt.engine_path);
  std::vector<char> data((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
  size_t off = 0;
  int meta_h = 0, meta_w = 0;
  if (data.size() > 4) {  // Ultralytics header: uint32 LE length + JSON metadata
    uint32_t n;
    std::memcpy(&n, data.data(), 4);
    if (n > 0 && n + 4 < data.size() && data[4] == '{') {
      parse_meta(std::string(data.data() + 4, n), names_, meta_h, meta_w);
      off = 4 + n;
    }
  }
  CUDA_CHECK(cudaStreamCreate(&impl_->stream));
  impl_->runtime.reset(nvinfer1::createInferRuntime(g_logger));
  impl_->engine.reset(impl_->runtime->deserializeCudaEngine(data.data() + off, data.size() - off));
  if (!impl_->engine) throw std::runtime_error("TensorRT: cannot deserialize " + opt.engine_path);
  impl_->ctx.reset(impl_->engine->createExecutionContext());
  for (int i = 0; i < impl_->engine->getNbIOTensors(); ++i) {
    const char *nm = impl_->engine->getIOTensorName(i);
    const auto dims = impl_->engine->getTensorShape(nm);
    if (impl_->engine->getTensorIOMode(nm) == nvinfer1::TensorIOMode::kINPUT) {
      impl_->in_name = nm;
      in_h_ = (int)dims.d[2];
      in_w_ = (int)dims.d[3];
    } else if (dims.nbDims == 3) {
      impl_->out0_name = nm;
      na_ = (int)dims.d[2];
      const int ch = (int)dims.d[1];
      nm_ = 32;
      nc_ = names_.empty() ? ch - 4 - nm_ : (int)names_.size();
      nm_ = ch - 4 - nc_;
    } else if (dims.nbDims == 4) {
      impl_->out1_name = nm;
      mh_ = (int)dims.d[2];
      mw_ = (int)dims.d[3];
    }
    if (impl_->engine->getTensorDataType(nm) != nvinfer1::DataType::kFLOAT)
      throw std::runtime_error("YoloTrtSegmenter: expected float32 engine I/O");
  }
  if (in_h_ <= 0 || in_w_ <= 0 || in_h_ < 0) throw std::runtime_error("YoloTrtSegmenter: dynamic engines not supported");
  if (names_.empty())
    for (int i = 0; i < nc_; ++i) names_[i] = std::to_string(i);
  impl_->d_in.reserve(sizeof(float) * 3 * in_h_ * in_w_);
  impl_->d_out0.reserve(sizeof(float) * (4 + nc_ + nm_) * na_);
  impl_->d_out1.reserve(sizeof(float) * nm_ * mh_ * mw_);
  impl_->h_out0.resize((size_t)(4 + nc_ + nm_) * na_);
  impl_->ctx->setTensorAddress(impl_->in_name.c_str(), impl_->d_in.p);
  impl_->ctx->setTensorAddress(impl_->out0_name.c_str(), impl_->d_out0.p);
  impl_->ctx->setTensorAddress(impl_->out1_name.c_str(), impl_->d_out1.p);
  float lut[256];
  const float inv = 1.0f / 255.0f;
  for (int v = 0; v < 256; ++v) lut[v] = (float)v * inv;
  impl_->d_lut.reserve(sizeof(lut));
  CUDA_CHECK(cudaMemcpy(impl_->d_lut.p, lut, sizeof(lut), cudaMemcpyHostToDevice));
  if (!opt.classes.empty()) {
    filter_ = true;
    std::set<std::string> wanted;
    for (const auto &c : opt.classes) wanted.insert(norm_name(c));
    for (const auto &kv : names_) {
      std::string l = kv.second;
      std::transform(l.begin(), l.end(), l.begin(), [](unsigned char ch) { return std::tolower(ch); });
      if (wanted.count(l)) class_ids_.push_back(kv.first);
    }
    std::sort(class_ids_.begin(), class_ids_.end());
  }
  (void)meta_h;
  (void)meta_w;
}

YoloTrtSegmenter::~YoloTrtSegmenter() = default;

void YoloTrtSegmenter::warmup(int h, int w) { predict(cv::Mat::zeros(h, w, CV_8UC3)); }

std::vector<Instance> YoloTrtSegmenter::predict(const cv::Mat &image_in) {
  const auto t0 = Clock::now();
  if (filter_ && class_ids_.empty()) return {};
  Impl &I = *impl_;
  cv::Mat img = image_in;
  if (img.channels() == 4) cv::cvtColor(img, img, cv::COLOR_BGRA2BGR);
  const int h = img.rows, w = img.cols;
  // ---- LetterBox (ultralytics.data.augment.LetterBox, center=True, auto=False for static engines)
  const double r = std::min((double)in_h_ / h, (double)in_w_ / w);
  const int nw = (int)std::nearbyint(w * r), nh = (int)std::nearbyint(h * r);
  const double dw = (in_w_ - nw) / 2.0, dh = (in_h_ - nh) / 2.0;
  const int top = (int)std::nearbyint(dh - 0.1), left = (int)std::nearbyint(dw - 0.1);
  if (nw != w || nh != h) {
    cv::Mat bgr = img;
    if (img.channels() == 1) cv::cvtColor(img, bgr, cv::COLOR_GRAY2BGR);
    cv::resize(bgr, img, cv::Size(nw, nh), 0, 0, cv::INTER_LINEAR);
  }
  if (!img.isContinuous()) img = img.clone();
  const int sc = img.channels();
  I.d_src.reserve(img.total() * sc);
  CUDA_CHECK(cudaMemcpyAsync(I.d_src.p, img.data, img.total() * sc, cudaMemcpyHostToDevice, I.stream));
  savior_cuda::launch_preprocess((const uint8_t *)I.d_src.p, img.rows, img.cols, sc, (int)img.step, (float *)I.d_in.p,
                                 in_h_, in_w_, top, left, (const float *)I.d_lut.p, I.stream);
  const auto t1 = Clock::now();
  if (!I.ctx->enqueueV3(I.stream)) throw std::runtime_error("TensorRT enqueueV3 failed");
  CUDA_CHECK(cudaMemcpyAsync(I.h_out0.data(), I.d_out0.p, I.h_out0.size() * sizeof(float), cudaMemcpyDeviceToHost,
                             I.stream));
  CUDA_CHECK(cudaStreamSynchronize(I.stream));
  const auto t2 = Clock::now();
  // ---- NMS (ultralytics.utils.nms.non_max_suppression + torchvision.ops.nms)
  const float conf_thr = (float)opt_.conf;
  const float *o = I.h_out0.data();
  const int A = na_;
  struct Cand {
    float b[4], conf, cls;
    int anchor;
  };
  std::vector<Cand> cand;
  for (int a = 0; a < A; ++a) {
    float best = o[(size_t)4 * A + a];
    int j = 0;
    for (int k = 1; k < nc_; ++k) {
      const float v = o[(size_t)(4 + k) * A + a];
      if (v > best) {
        best = v;
        j = k;
      }
    }
    if (!(best > conf_thr)) continue;
    if (filter_ && !std::binary_search(class_ids_.begin(), class_ids_.end(), j)) continue;
    const float cx = o[a], cy = o[(size_t)A + a], bw = o[(size_t)2 * A + a], bh = o[(size_t)3 * A + a];
    const float hw = bw / 2, hh = bh / 2;
    cand.push_back({{cx - hw, cy - hh, cx + hw, cy + hh}, best, (float)j, a});
  }
  std::vector<int> order(cand.size());
  std::iota(order.begin(), order.end(), 0);
  std::stable_sort(order.begin(), order.end(), [&cand](int x, int y) { return cand[x].conf > cand[y].conf; });
  const float iou_thr = (float)opt_.iou;
  std::vector<std::array<float, 4>> ob(cand.size());
  for (size_t i = 0; i < cand.size(); ++i) {
    const float c = cand[i].cls * 7680.0f;
    for (int k = 0; k < 4; ++k) ob[i][k] = cand[i].b[k] + c;
  }
  std::vector<uint8_t> removed(cand.size(), 0);
  std::vector<int> keep;
  for (size_t ii = 0; ii < order.size(); ++ii) {
    const int i = order[ii];
    if (removed[ii]) continue;
    keep.push_back(i);
    if ((int)keep.size() >= opt_.max_det) break;
    const auto &a = ob[i];
    const float Sa = (a[2] - a[0]) * (a[3] - a[1]);
    for (size_t jj = ii + 1; jj < order.size(); ++jj) {
      if (removed[jj]) continue;
      const auto &b = ob[order[jj]];
      const float left_ = std::max(a[0], b[0]), right_ = std::min(a[2], b[2]);
      const float top_ = std::max(a[1], b[1]), bottom_ = std::min(a[3], b[3]);
      const float width = std::max(right_ - left_, 0.f), height = std::max(bottom_ - top_, 0.f);
      const float interS = width * height;
      const float Sb = (b[2] - b[0]) * (b[3] - b[1]);
      if (interS / (Sa + Sb - interS) > iou_thr) removed[jj] = 1;
    }
  }
  const int N = (int)keep.size();
  // ---- scale_boxes (img1 = network input, img0 = original image) + clip
  const double gain = std::min((double)in_h_ / h, (double)in_w_ / w);
  const int new_h = (int)std::nearbyint(h * gain), new_w = (int)std::nearbyint(w * gain);
  const double gain_y = (double)new_h / h, gain_x = (double)new_w / w;
  const int pad_x = (int)std::nearbyint((in_w_ - new_w) / 2.0 - 0.1), pad_y = (int)std::nearbyint((in_h_ - new_h) / 2.0 - 0.1);
  const float igx = 1.0f / (float)gain_x, igy = 1.0f / (float)gain_y;
  std::vector<float> fbox(4 * N), coef((size_t)N * nm_), confs(N);
  std::vector<int> cls(N), ibox(4 * N);
  std::vector<long long> offs(N + 1, 0);
  for (int n = 0; n < N; ++n) {
    const Cand &c = cand[keep[n]];
    float x1 = (c.b[0] - (float)pad_x) * igx, y1 = (c.b[1] - (float)pad_y) * igy;
    float x2 = (c.b[2] - (float)pad_x) * igx, y2 = (c.b[3] - (float)pad_y) * igy;
    x1 = std::min(std::max(x1, 0.f), (float)w);
    x2 = std::min(std::max(x2, 0.f), (float)w);
    y1 = std::min(std::max(y1, 0.f), (float)h);
    y2 = std::min(std::max(y2, 0.f), (float)h);
    fbox[4 * n] = x1; fbox[4 * n + 1] = y1; fbox[4 * n + 2] = x2; fbox[4 * n + 3] = y2;
    confs[n] = c.conf;
    cls[n] = (int)c.cls;
    for (int k = 0; k < nm_; ++k) coef[(size_t)n * nm_ + k] = o[(size_t)(4 + nc_ + k) * A + c.anchor];
    int bx0 = (int)std::min(std::max(std::floor(x1), 0.f), (float)w), by0 = (int)std::min(std::max(std::floor(y1), 0.f), (float)h);
    int bx1 = (int)std::min(std::max(std::ceil(x2), 0.f), (float)w), by1 = (int)std::min(std::max(std::ceil(y2), 0.f), (float)h);
    bx1 = std::max(bx1, bx0);
    by1 = std::max(by1, by0);
    ibox[4 * n] = bx0; ibox[4 * n + 1] = by0; ibox[4 * n + 2] = bx1; ibox[4 * n + 3] = by1;
    offs[n + 1] = offs[n] + (long long)(bx1 - bx0) * (by1 - by0);
  }
  const auto t3 = Clock::now();
  std::vector<Instance> out;
  if (N == 0) {
    t_ = {ms(t0, t1), ms(t1, t2), ms(t2, t3), 0.0, ms(t0, t3)};
    return out;
  }
  // ---- process_mask_native
  const int P = mh_ * mw_;
  I.d_coef.reserve(sizeof(float) * coef.size());
  I.d_logits.reserve(sizeof(float) * (size_t)N * P);
  I.d_fbox.reserve(sizeof(float) * fbox.size());
  I.d_ibox.reserve(sizeof(int) * ibox.size());
  I.d_offs.reserve(sizeof(long long) * offs.size());
  I.d_masks.reserve(std::max<long long>(1, offs[N]));
  CUDA_CHECK(cudaMemcpyAsync(I.d_coef.p, coef.data(), sizeof(float) * coef.size(), cudaMemcpyHostToDevice, I.stream));
  CUDA_CHECK(cudaMemcpyAsync(I.d_fbox.p, fbox.data(), sizeof(float) * fbox.size(), cudaMemcpyHostToDevice, I.stream));
  CUDA_CHECK(cudaMemcpyAsync(I.d_ibox.p, ibox.data(), sizeof(int) * ibox.size(), cudaMemcpyHostToDevice, I.stream));
  CUDA_CHECK(cudaMemcpyAsync(I.d_offs.p, offs.data(), sizeof(long long) * offs.size(), cudaMemcpyHostToDevice, I.stream));
  savior_cuda::launch_logits((const float *)I.d_coef.p, (const float *)I.d_out1.p, (float *)I.d_logits.p, N, nm_, P,
                             I.stream);
  const double mg = std::min(4.0 * mh_ / h, 4.0 * mw_ / w);
  const int pad = (4 * mh_ - (int)std::nearbyint(h * mg)) | (4 * mw_ - (int)std::nearbyint(w * mg));
  const int f = 4 / std::gcd(4, pad | (pad / 2));
  const float *src = (const float *)I.d_logits.p;
  int Hs = mh_, Ws = mw_;
  if (f > 1) {
    I.d_up.reserve(sizeof(float) * (size_t)N * P * f * f);
    savior_cuda::launch_upsample(src, (float *)I.d_up.p, N, mh_, mw_, f, I.stream);
    src = (const float *)I.d_up.p;
    Hs *= f;
    Ws *= f;
  }
  int stop = 0, sleft = 0, sih = Hs, siw = Ws, resize = 0;
  if (!(Hs == h && Ws == w)) {  // ultralytics.utils.ops.scale_masks (ratio_pad None, padding True)
    const double g2 = std::min((double)Hs / h, (double)Ws / w);
    const double pw = (Ws - std::nearbyint(w * g2)) / 2.0, ph = (Hs - std::nearbyint(h * g2)) / 2.0;
    stop = (int)std::nearbyint(ph - 0.1);
    sleft = (int)std::nearbyint(pw - 0.1);
    sih = (int)std::nearbyint(h * g2);
    siw = (int)std::nearbyint(w * g2);
    resize = 1;
  }
  savior_cuda::launch_masks(src, Hs, Ws, stop, sleft, sih, siw, h, w, resize, (const float *)I.d_fbox.p,
                            (const int *)I.d_ibox.p, (const long long *)I.d_offs.p, (uint8_t *)I.d_masks.p, N, I.stream);
  I.h_masks.resize(std::max<long long>(1, offs[N]));
  CUDA_CHECK(cudaMemcpyAsync(I.h_masks.data(), I.d_masks.p, offs[N], cudaMemcpyDeviceToHost, I.stream));
  CUDA_CHECK(cudaStreamSynchronize(I.stream));
  for (int n = 0; n < N; ++n) {
    const int x0 = ibox[4 * n], y0 = ibox[4 * n + 1], x1 = ibox[4 * n + 2], y1 = ibox[4 * n + 3];
    const long long a = offs[n], b = offs[n + 1];
    bool any = false;
    for (long long k = a; k < b && !any; ++k) any = I.h_masks[k] != 0;
    if (!any) continue;
    cv::Mat m = cv::Mat::zeros(h, w, CV_8U);
    cv::Mat crop(y1 - y0, x1 - x0, CV_8U, I.h_masks.data() + a);
    crop.copyTo(m(cv::Rect(x0, y0, x1 - x0, y1 - y0)));
    const Box bb{x0, y0, x1, y1};
    auto it = names_.find(cls[n]);
    out.emplace_back(m, it != names_.end() ? it->second : std::to_string(cls[n]), (double)confs[n], &bb);
  }
  const auto t4 = Clock::now();
  t_ = {ms(t0, t1), ms(t1, t2), ms(t2, t3), ms(t3, t4), ms(t0, t4)};
  return out;
}

}  // namespace savior
