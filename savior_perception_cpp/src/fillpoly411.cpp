// SPDX-License-Identifier: Apache-2.0
// Polygon fill of OpenCV 4.11.0 (modules/imgproc/src/drawing.cpp: cv::fillPoly -> CollectPolyEdges + FillEdgeCollection,
// with the edge outline drawn by Line / LineIterator / clipLine), restricted to what savior needs: one polygon, CV_8UC1,
// LINE_8, shift 0, offset (0, 0). Vendored so that the right-mask warp is bit-identical to the Python node (cv2 4.11.0)
// whatever OpenCV the C++ node links: OpenCV <= 4.9 (Ubuntu 22.04 / ROS Humble 4.5.4, JetPack 6 4.8.0) clips polygons
// that leave the image differently (CollectPolyEdges changed in 4.10), which changed a few right-mask pixels per frame.
//
// Copyright (C) 2000-2008, Intel Corporation, all rights reserved.
// Copyright (C) 2009, Willow Garage Inc., all rights reserved.
// Copyright (C) 2015-2025, OpenCV Foundation and contributors (Apache License 2.0, https://opencv.org/license/).
#include <algorithm>
#include <climits>
#include <cstdint>
#include <cstring>
#include <vector>

#include <opencv2/core.hpp>

namespace savior {
namespace {

enum { XY_SHIFT = 16, XY_ONE = 1 << XY_SHIFT };

struct PolyEdge {
  int y0 = 0, y1 = 0;
  int64_t x = 0, dx = 0;
  PolyEdge *next = nullptr;
};

bool clip_line_l(int64_t w, int64_t h, int64_t &x1, int64_t &y1, int64_t &x2, int64_t &y2) {
  int c1, c2;
  const int64_t right = w - 1, bottom = h - 1;
  if (w <= 0 || h <= 0) return false;
  c1 = (x1 < 0) + (x1 > right) * 2 + (y1 < 0) * 4 + (y1 > bottom) * 8;
  c2 = (x2 < 0) + (x2 > right) * 2 + (y2 < 0) * 4 + (y2 > bottom) * 8;
  if ((c1 & c2) == 0 && (c1 | c2) != 0) {
    int64_t a;
    if (c1 & 12) {
      a = c1 < 8 ? 0 : bottom;
      x1 += (int64_t)((double)(a - y1) * (x2 - x1) / (y2 - y1));
      y1 = a;
      c1 = (x1 < 0) + (x1 > right) * 2;
    }
    if (c2 & 12) {
      a = c2 < 8 ? 0 : bottom;
      x2 += (int64_t)((double)(a - y2) * (x2 - x1) / (y2 - y1));
      y2 = a;
      c2 = (x2 < 0) + (x2 > right) * 2;
    }
    if ((c1 & c2) == 0 && (c1 | c2) != 0) {
      if (c1) {
        a = c1 == 1 ? 0 : right;
        y1 += (int64_t)((double)(a - x1) * (y2 - y1) / (x2 - x1));
        x1 = a;
        c1 = 0;
      }
      if (c2) {
        a = c2 == 1 ? 0 : right;
        y2 += (int64_t)((double)(a - x2) * (y2 - y1) / (x2 - x1));
        x2 = a;
        c2 = 0;
      }
    }
  }
  return (c1 | c2) == 0;
}

// int-point clipLine (cv::clipLine(Size, Point&, Point&) of 4.11: through the int64 version)
bool clip_line_i(int w, int h, int &x1, int &y1, int &x2, int &y2) {
  int64_t a = x1, b = y1, c = x2, d = y2;
  const bool in = clip_line_l(w, h, a, b, c, d);
  x1 = (int)a; y1 = (int)b; x2 = (int)c; y2 = (int)d;
  return in;
}

// Line(img, pt1, pt2, color, 8): LineIterator(img, pt1, pt2, 8, leftToRight=true) of 4.11
void line8(cv::Mat &img, cv::Point pt1, cv::Point pt2, uint8_t color) {
  const int W = img.cols, H = img.rows;
  if ((unsigned)pt1.x >= (unsigned)W || (unsigned)pt2.x >= (unsigned)W || (unsigned)pt1.y >= (unsigned)H ||
      (unsigned)pt2.y >= (unsigned)H) {
    if (!clip_line_i(W, H, pt1.x, pt1.y, pt2.x, pt2.y)) return;
  }
  int delta_x = 1, delta_y = 1;
  int dx = pt2.x - pt1.x, dy = pt2.y - pt1.y;
  if (dx < 0) {  // leftToRight
    dx = -dx;
    dy = -dy;
    pt1 = pt2;
  }
  if (dy < 0) {
    dy = -dy;
    delta_y = -1;
  }
  const bool vert = dy > dx;
  if (vert) {
    std::swap(dx, dy);
    std::swap(delta_x, delta_y);
  }
  int err = dx - (dy + dy);
  const int plusDelta = dx + dx, minusDelta = -(dy + dy);
  int minusShift = delta_x, plusShift = 0, minusStep = 0, plusStep = delta_y;
  const int count = dx + 1;
  if (vert) {
    std::swap(plusStep, plusShift);
    std::swap(minusStep, minusShift);
  }
  const int step = (int)img.step;
  uint8_t *ptr = img.ptr<uint8_t>() + (size_t)pt1.y * step + (size_t)pt1.x;
  const int pS = plusStep * step + plusShift, mS = minusStep * step + minusShift;
  for (int i = 0; i < count; ++i) {
    *ptr = color;
    const int mask = err < 0 ? -1 : 0;
    err += minusDelta + (plusDelta & mask);
    ptr += mS + (pS & mask);
  }
}

void collect_poly_edges(cv::Mat &img, const std::vector<cv::Point> &v, std::vector<PolyEdge> &edges, uint8_t color) {
  const int count = (int)v.size();
  const int delta = 0;  // offset.y + ((1 << shift) >> 1), shift = 0
  int64_t p0x = (int64_t)v[count - 1].x << XY_SHIFT, p0y = (int64_t)v[count - 1].y + delta;
  edges.reserve(edges.size() + count);
  for (int i = 0; i < count; ++i) {
    const int64_t p1x = (int64_t)v[i].x << XY_SHIFT, p1y = (int64_t)v[i].y + delta;
    int64_t c0x = p0x, c0y = p0y, c1x = p1x, c1y = p1y;
    cv::Point t0((int)((p0x + (XY_ONE >> 1)) >> XY_SHIFT), (int)p0y), t1((int)((p1x + (XY_ONE >> 1)) >> XY_SHIFT), (int)p1y);
    line8(img, t0, t1, color);
    if ((unsigned)t0.x >= (unsigned)img.cols || (unsigned)t1.x >= (unsigned)img.cols ||
        (unsigned)t0.y >= (unsigned)img.rows || (unsigned)t1.y >= (unsigned)img.rows) {
      clip_line_i(img.cols, img.rows, t0.x, t0.y, t1.x, t1.y);
      if (t0.y != t1.y) {
        c0y = t0.y;
        c1y = t1.y;
      }
    }
    c0x = (int64_t)t0.x << XY_SHIFT;
    c1x = (int64_t)t1.x << XY_SHIFT;
    if (p0y != p1y) {
      PolyEdge e;
      e.dx = (c1x - c0x) / (c1y - c0y);
      if (p0y < p1y) {
        e.y0 = (int)p0y;
        e.y1 = (int)p1y;
        e.x = c0x + (p0y - c0y) * e.dx;
      } else {
        e.y0 = (int)p1y;
        e.y1 = (int)p0y;
        e.x = c1x + (p1y - c1y) * e.dx;
      }
      edges.push_back(e);
    }
    p0x = p1x;
    p0y = p1y;
  }
}

void fill_edge_collection(cv::Mat &img, std::vector<PolyEdge> &edges, uint8_t color) {
  PolyEdge tmp;
  int i, y, total = (int)edges.size();
  const int W = img.cols, H = img.rows;
  PolyEdge *e;
  int y_max = INT_MIN, y_min = INT_MAX;
  int64_t x_max = (int64_t)0xFFFFFFFFFFFFFFFF, x_min = 0x7FFFFFFFFFFFFFFF;
  const int delta = XY_ONE - 1;
  if (total < 2) return;
  for (i = 0; i < total; i++) {
    PolyEdge &e1 = edges[i];
    const int64_t x1 = e1.x + (e1.y1 - e1.y0) * e1.dx;
    y_min = std::min(y_min, e1.y0);
    y_max = std::max(y_max, e1.y1);
    x_min = std::min(x_min, e1.x);
    x_max = std::max(x_max, e1.x);
    x_min = std::min(x_min, x1);
    x_max = std::max(x_max, x1);
  }
  if (y_max < 0 || y_min >= H || x_max < 0 || x_min >= ((int64_t)W << XY_SHIFT)) return;
  std::sort(edges.begin(), edges.end(), [](const PolyEdge &e1, const PolyEdge &e2) {
    return e1.y0 - e2.y0 ? e1.y0 < e2.y0 : e1.x - e2.x ? e1.x < e2.x : e1.dx < e2.dx;
  });
  tmp.y0 = INT_MAX;
  edges.push_back(tmp);
  i = 0;
  tmp.next = nullptr;
  e = &edges[i];
  y_max = std::min(y_max, H);
  for (y = e->y0; y < y_max; y++) {
    PolyEdge *last, *prelast, *keep_prelast;
    int draw = 0;
    const int clipline = y < 0;
    prelast = &tmp;
    last = tmp.next;
    while (last || e->y0 == y) {
      if (last && last->y1 == y) {
        prelast->next = last->next;
        last = last->next;
        continue;
      }
      keep_prelast = prelast;
      if (last && (e->y0 > y || last->x < e->x)) {
        prelast = last;
        last = last->next;
      } else if (i < total) {
        prelast->next = e;
        e->next = last;
        prelast = e;
        e = &edges[++i];
      } else {
        break;
      }
      if (draw) {
        if (!clipline) {
          uint8_t *timg = img.ptr<uint8_t>(y);
          int x1, x2;
          if (keep_prelast->x > prelast->x) {
            x1 = (int)((prelast->x + delta) >> XY_SHIFT);
            x2 = (int)(keep_prelast->x >> XY_SHIFT);
          } else {
            x1 = (int)((keep_prelast->x + delta) >> XY_SHIFT);
            x2 = (int)(prelast->x >> XY_SHIFT);
          }
          if (x1 < W && x2 >= 0) {
            if (x1 < 0) x1 = 0;
            if (x2 >= W) x2 = W - 1;
            if (x2 >= x1) std::memset(timg + x1, color, x2 - x1 + 1);  // ICV_HLINE (1-channel)
          }
        }
        keep_prelast->x += keep_prelast->dx;
        prelast->x += prelast->dx;
      }
      draw ^= 1;
    }
    // sort edges (bubble sort)
    keep_prelast = nullptr;
    do {
      prelast = &tmp;
      last = tmp.next;
      PolyEdge *last_exchange = nullptr;
      while (last != keep_prelast && last->next != nullptr) {
        PolyEdge *te = last->next;
        if (last->x > te->x) {
          prelast->next = te;
          last->next = te->next;
          te->next = last;
          prelast = te;
          last_exchange = prelast;
        } else {
          prelast = last;
          last = te;
        }
      }
      if (last_exchange == nullptr) break;
      keep_prelast = last_exchange;
    } while (keep_prelast != tmp.next && keep_prelast != &tmp);
  }
}

}  // namespace

void fill_poly_cv411(cv::Mat &img, const std::vector<cv::Point> &pts, uint8_t color) {
  CV_Assert(img.type() == CV_8UC1);
  if (pts.empty()) return;
  std::vector<PolyEdge> edges;
  edges.reserve(pts.size() + 1);
  collect_poly_edges(img, pts, edges, color);
  fill_edge_collection(img, edges, color);
}

}  // namespace savior
