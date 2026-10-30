#!/usr/bin/env python3
"""test_fillpoly.py [n]: savior_cpp.cvops.fillpoly411 (vendored OpenCV 4.11 polygon fill) vs cv2.fillPoly of the Python node's
cv2 4.11 and vs the linked OpenCV's cv::fillPoly, on random polygons (convex / concave / self-intersecting, inside and
crossing the image border, the shapes of the right-mask warp: up to ~1000 points, outside by up to 80 px)."""
import sys
import cv2
import numpy as np
import savior_cpp

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
rs = np.random.RandomState(0)
H, W = 376, 672
bad411 = badlink = 0
for k in range(n):
    m = rs.randint(3, 60 if k % 3 else 1000)
    cx, cy = rs.uniform(-80, W + 80), rs.uniform(-80, H + 80)
    if k % 2:
        ang = np.sort(rs.uniform(0, 2 * np.pi, m))
        r = rs.uniform(5, 150) * (1 + 0.3 * rs.randn(m))
        pts = np.column_stack([cx + r * np.cos(ang), cy + r * np.sin(ang)])
    else:
        pts = np.column_stack([cx + rs.uniform(-150, 150, m), cy + rs.uniform(-150, 150, m)])
    pts = np.rint(pts).astype(np.int32)
    a = np.zeros((H, W), np.uint8)
    cv2.fillPoly(a, [pts.reshape(-1, 1, 2)], 255)
    b = savior_cpp.cvops.fillpoly411(H, W, [pts], 255)
    c = savior_cpp.cvops.fillpoly(H, W, [pts], 255)
    bad411 += int(not np.array_equal(a, b))
    badlink += int(not np.array_equal(a, c))
print(f'polygons {n}: vendored 4.11 fill != cv2 {cv2.__version__}: {bad411}; linked OpenCV {savior_cpp.opencv_version} cv::fillPoly != cv2: {badlink}')
