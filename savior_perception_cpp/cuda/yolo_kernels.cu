// SPDX-License-Identifier: GPL-3.0-or-later
// CUDA kernels of the YOLO26-seg TensorRT segmenter (pre-processing, mask logits, PyTorch-equivalent bilinear
// upsampling of the prototype logits, threshold + crop into compact per-detection box buffers).
#include <cstdint>

#include <cuda_runtime.h>

namespace savior_cuda {

// letterboxed (already resized) source -> CHW float RGB, pad value 114; lut[v] = v * (1/255) exactly like torch div_
__global__ void k_preprocess(const uint8_t *src, int sh, int sw, int sc, int sstep, float *dst, int H, int W, int top,
                             int left, const float *lut) {
  const int x = blockIdx.x * blockDim.x + threadIdx.x, y = blockIdx.y * blockDim.y + threadIdx.y;
  if (x >= W || y >= H) return;
  const int sx = x - left, sy = y - top;
  uint8_t bgr[3] = {114, 114, 114};
  if (sx >= 0 && sx < sw && sy >= 0 && sy < sh) {
    const uint8_t *p = src + (size_t)sy * sstep + (size_t)sx * sc;
    if (sc == 1) bgr[0] = bgr[1] = bgr[2] = p[0];
    else { bgr[0] = p[0]; bgr[1] = p[1]; bgr[2] = p[2]; }
  }
  const size_t plane = (size_t)H * W, o = (size_t)y * W + x;
  dst[o] = lut[bgr[2]];             // R
  dst[plane + o] = lut[bgr[1]];     // G
  dst[2 * plane + o] = lut[bgr[0]]; // B
}

// logits[n][p] = sum_k coef[n][k] * proto[k][p]
__global__ void k_logits(const float *coef, const float *proto, float *logits, int N, int nm, int P) {
  const int p = blockIdx.x * blockDim.x + threadIdx.x, n = blockIdx.y;
  if (p >= P || n >= N) return;
  float s = 0.f;
  for (int k = 0; k < nm; ++k) s = fmaf(coef[n * nm + k], proto[(size_t)k * P + p], s);
  logits[(size_t)n * P + p] = s;
}

// PyTorch upsample_bilinear2d (align_corners=false) of a [sy0, sy0+ih) x [sx0, sx0+iw) window of a (N, Hs, Ws) stack
__device__ __forceinline__ float bilinear(const float *img, int Ws, int sy0, int sx0, int ih, int iw, float rh, float rw,
                                          int oy, int ox) {
  float h1r = rh * ((float)oy + 0.5f) - 0.5f;
  h1r = h1r < 0.f ? 0.f : h1r;
  const int h1 = (int)h1r;
  const int h1p = (h1 < ih - 1) ? 1 : 0;
  const float h1lambda = h1r - h1;
  const float h0lambda = 1.f - h1lambda;
  float w1r = rw * ((float)ox + 0.5f) - 0.5f;
  w1r = w1r < 0.f ? 0.f : w1r;
  const int w1 = (int)w1r;
  const int w1p = (w1 < iw - 1) ? 1 : 0;
  const float w1lambda = w1r - w1;
  const float w0lambda = 1.f - w1lambda;
  const float *r0 = img + (size_t)(sy0 + h1) * Ws + sx0;
  const float *r1 = img + (size_t)(sy0 + h1 + h1p) * Ws + sx0;
  return h0lambda * (w0lambda * r0[w1] + w1lambda * r0[w1 + w1p]) +
         h1lambda * (w0lambda * r1[w1] + w1lambda * r1[w1 + w1p]);
}

// F.interpolate(scale_factor=f, bilinear): (N, H, W) -> (N, fH, fW), scale = 1/f
__global__ void k_upsample(const float *in, float *out, int N, int H, int W, int f) {
  const int ox = blockIdx.x * blockDim.x + threadIdx.x, oy = blockIdx.y * blockDim.y + threadIdx.y, n = blockIdx.z;
  const int OH = H * f, OW = W * f;
  if (ox >= OW || oy >= OH || n >= N) return;
  const float r = (float)(1.0 / (double)f);
  out[((size_t)n * OH + oy) * OW + ox] = bilinear(in + (size_t)n * H * W, W, 0, 0, H, W, r, r, oy, ox);
}

// per detection: integer box crop of the image-size mask = (bilinear(window -> oh x ow) > 0) & inside the float box
__global__ void k_masks(const float *logits, int Hs, int Ws, int top, int left, int ih, int iw, int oh, int ow,
                        int resize, const float *fbox, const int *ibox, const long long *offs, uint8_t *out, int N) {
  const int n = blockIdx.y;
  if (n >= N) return;
  const int x0 = ibox[4 * n], y0 = ibox[4 * n + 1], x1 = ibox[4 * n + 2], y1 = ibox[4 * n + 3];
  const int bw = x1 - x0, area = bw * (y1 - y0);
  const float fx1 = fbox[4 * n], fy1 = fbox[4 * n + 1], fx2 = fbox[4 * n + 2], fy2 = fbox[4 * n + 3];
  const float rh = (float)ih / (float)oh, rw = (float)iw / (float)ow;
  const float *img = logits + (size_t)n * Hs * Ws;
  for (int k = blockIdx.x * blockDim.x + threadIdx.x; k < area; k += gridDim.x * blockDim.x) {
    const int y = y0 + k / bw, x = x0 + k % bw;
    float v;
    if (resize) v = bilinear(img, Ws, top, left, ih, iw, rh, rw, y, x);
    else v = img[(size_t)y * Ws + x];
    const bool in = ((float)x >= fx1) && ((float)x < fx2) && ((float)y >= fy1) && ((float)y < fy2);
    out[offs[n] + k] = (v > 0.f && in) ? 1 : 0;
  }
}

void launch_preprocess(const uint8_t *src, int sh, int sw, int sc, int sstep, float *dst, int H, int W, int top, int left,
                       const float *lut, cudaStream_t st) {
  dim3 b(32, 8), g((W + 31) / 32, (H + 7) / 8);
  k_preprocess<<<g, b, 0, st>>>(src, sh, sw, sc, sstep, dst, H, W, top, left, lut);
}

void launch_logits(const float *coef, const float *proto, float *logits, int N, int nm, int P, cudaStream_t st) {
  if (N <= 0) return;
  dim3 b(256), g((P + 255) / 256, N);
  k_logits<<<g, b, 0, st>>>(coef, proto, logits, N, nm, P);
}

void launch_upsample(const float *in, float *out, int N, int H, int W, int f, cudaStream_t st) {
  if (N <= 0) return;
  dim3 b(32, 8), g((W * f + 31) / 32, (H * f + 7) / 8, N);
  k_upsample<<<g, b, 0, st>>>(in, out, N, H, W, f);
}

void launch_masks(const float *logits, int Hs, int Ws, int top, int left, int ih, int iw, int oh, int ow, int resize,
                  const float *fbox, const int *ibox, const long long *offs, uint8_t *out, int N, cudaStream_t st) {
  if (N <= 0) return;
  dim3 b(256), g(64, N);
  k_masks<<<g, b, 0, st>>>(logits, Hs, Ws, top, left, ih, iw, oh, ow, resize, fbox, ibox, offs, out, N);
}

}  // namespace savior_cuda
