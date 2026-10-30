# OpenCV primitives of the pipeline: C++ build OpenCV vs Python cv2 4.11.0.86 (same calls / arguments, real t1 frames)

tools/cv_version_diff.py (hall_t1_L3 + aisles_t1_L3, 60 frames each) + tools/test_fillpoly.py (20 000 random polygons, inside and crossing the image border).

| primitive | calls | identical (C++ OpenCV 4.5.4) | identical (C++ OpenCV 4.11.0) |
|---|--:|--:|--:|
| resize INTER_AREA | 120 | 120 | 120 |
| goodFeaturesToTrack (background) | 120 | 120 | 120 |
| goodFeaturesToTrack (instance crop) | 2122 | 2122 | 2122 |
| erode 3x3 x2 | 2122 | 2122 | 2122 |
| dilate ellipse r4 | 2122 | 2122 | 2122 |
| findContours EXTERNAL/NONE | 2122 | 2122 | 2122 |
| fillPoly (same polygons) | 2122 | 2122 | 2122 |
| StereoSGBM 3-way | 566 | 566 | 566 |
| calcOpticalFlowPyrLK | 118 | 118 | 118 |
| cv::fillPoly, random polygons | 20000 | 7757 (4.5.4), 2537 (4.8.0) | 20000 |
| savior::fill_poly_cv411 (vendored 4.11 fill), random polygons | 20000 | 20000 (4.5.4), 20000 (4.8.0) | 20000 |

Also identical (4.5.4 vs cv2 4.11): undistortPoints (iterative, both criteria), projectPoints, resize INTER_NEAREST, moments, circle (r 3 / 8), erode 7x7 / 13x13, calcOpticalFlowPyrLK with OPTFLOW_USE_INITIAL_FLOW, stereoRectify / initUndistortRectifyMap (rectification maps bit-identical).
The only version-dependent primitive found is the polygon fill (edge collection / border clipping of CollectPolyEdges changed between 4.8 and 4.11): with cv::fillPoly of 4.5.4 / 4.8.0 a few right-mask pixels per frame differ from the Python node (right-mask pixel disagreement 2.9e-7 = 1295 px in 17 736 frames, 1005 of 17 736 frames with >= 1 differing pixel, left masks and all decisions identical); the port therefore uses the vendored 4.11 fill and is bit-identical with all three OpenCV versions.
