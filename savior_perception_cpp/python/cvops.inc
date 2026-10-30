// OpenCV primitive wrappers (version-difference analysis: the same calls as the pipeline, exposed one by one)
namespace cvops {
py::array_t<uint8_t> resize_area(const py::array &img, int w, int h) {
  cv::Mat m = to_mat_u8(img), o;
  cv::resize(m, o, cv::Size(w, h), 0, 0, cv::INTER_AREA);
  return from_mat_u8(o);
}
py::array_t<float> gftt(const py::array &img, int n, double q, double mind, const py::array &mask, int bs) {
  cv::Mat m = to_mat_u8(img), mk = to_mat_u8(mask);
  std::vector<cv::Point2f> c;
  cv::goodFeaturesToTrack(m, c, n, q, mind, mk, bs);
  py::array_t<float> out({(py::ssize_t)c.size(), (py::ssize_t)2});
  for (size_t i = 0; i < c.size(); ++i) { out.mutable_at(i, 0) = c[i].x; out.mutable_at(i, 1) = c[i].y; }
  return out;
}
py::tuple lk(const py::array &a, const py::array &b, const py::array_t<float> &p0, int win, int lev) {
  cv::Mat A = to_mat_u8(a), Bm = to_mat_u8(b);
  std::vector<cv::Point2f> q0(p0.shape(0)), q1;
  for (size_t i = 0; i < q0.size(); ++i) q0[i] = cv::Point2f(p0.at(i, 0), p0.at(i, 1));
  std::vector<uchar> st;
  std::vector<float> err;
  cv::calcOpticalFlowPyrLK(A, Bm, q0, q1, st, err, cv::Size(win, win), lev,
                           cv::TermCriteria(cv::TermCriteria::COUNT | cv::TermCriteria::EPS, 20, 0.03), 0);
  py::array_t<float> o({(py::ssize_t)q1.size(), (py::ssize_t)2});
  py::array_t<uint8_t> s({(py::ssize_t)st.size()});
  for (size_t i = 0; i < q1.size(); ++i) { o.mutable_at(i, 0) = q1[i].x; o.mutable_at(i, 1) = q1[i].y; s.mutable_at(i) = st[i]; }
  return py::make_tuple(o, s);
}
py::array_t<int16_t> sgbm(const py::array &l, const py::array &r, int nd, int bs) {
  cv::Mat L = to_mat_u8(l), R = to_mat_u8(r), d;
  auto m = cv::StereoSGBM::create(0, nd, bs, 8 * bs * bs, 32 * bs * bs, 1, 0, 10, 50, 2, cv::StereoSGBM::MODE_SGBM_3WAY);
  m->compute(L, R, d);
  py::array_t<int16_t> o({d.rows, d.cols});
  std::memcpy(o.mutable_data(), d.data, d.total() * 2);
  return o;
}
py::array_t<uint8_t> remap_lin(const py::array &img, const py::array_t<float> &mx, const py::array_t<float> &my) {
  cv::Mat m = to_mat_u8(img), o;
  cv::Mat X((int)mx.shape(0), (int)mx.shape(1), CV_32F, (void *)mx.data()), Y((int)my.shape(0), (int)my.shape(1), CV_32F, (void *)my.data());
  cv::remap(m, o, X, Y, cv::INTER_LINEAR, cv::BORDER_CONSTANT, cv::Scalar(0));
  return from_mat_u8(o);
}
py::list contours(const py::array &img) {
  cv::Mat m = to_mat_u8(img);
  std::vector<std::vector<cv::Point>> cs;
  cv::findContours(m.clone(), cs, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_NONE);
  py::list out;
  for (auto &c : cs) {
    py::array_t<int> a({(py::ssize_t)c.size(), (py::ssize_t)2});
    for (size_t i = 0; i < c.size(); ++i) { a.mutable_at(i, 0) = c[i].x; a.mutable_at(i, 1) = c[i].y; }
    out.append(a);
  }
  return out;
}
py::array_t<uint8_t> fillpoly(int h, int w, const py::list &polys, int v) {
  cv::Mat m = cv::Mat::zeros(h, w, CV_8U);
  for (auto p : polys) {
    auto a = p.cast<py::array_t<int>>();
    std::vector<cv::Point> pts(a.shape(0));
    for (size_t i = 0; i < pts.size(); ++i) pts[i] = cv::Point(a.at(i, 0), a.at(i, 1));
    cv::fillPoly(m, std::vector<std::vector<cv::Point>>{pts}, cv::Scalar(v));
  }
  return from_mat_u8(m);
}
py::array_t<uint8_t> fillpoly411(int h, int w, const py::list &polys, int v) {
  cv::Mat m = cv::Mat::zeros(h, w, CV_8U);
  for (auto p : polys) {
    auto a = p.cast<py::array_t<int>>();
    std::vector<cv::Point> pts(a.shape(0));
    for (size_t i = 0; i < pts.size(); ++i) pts[i] = cv::Point(a.at(i, 0), a.at(i, 1));
    savior::fill_poly_cv411(m, pts, (uint8_t)v);
  }
  return from_mat_u8(m);
}
py::array_t<uint8_t> erode3(const py::array &img, int it) {
  cv::Mat m = to_mat_u8(img), o;
  cv::erode(m, o, cv::Mat::ones(3, 3, CV_8U), cv::Point(-1, -1), it);
  return from_mat_u8(o);
}
py::array_t<uint8_t> dilate_ell(const py::array &img, int r) {
  cv::Mat m = to_mat_u8(img), o;
  cv::dilate(m, o, cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(2 * r + 1, 2 * r + 1)));
  return from_mat_u8(o);
}
py::array_t<double> undistort(const py::array_t<double> &pts, const py::array_t<double> &K, const py::array_t<double> &D, int it, double eps) {
  cv::Mat src((int)pts.shape(0), 1, CV_64FC2, (void *)pts.data()), dst;
  cv::Mat k(3, 3, CV_64F, (void *)K.data()), d(1, 4, CV_64F, (void *)D.data());
  cv::undistortPoints(src, dst, k, d, cv::noArray(), cv::noArray(), cv::TermCriteria(cv::TermCriteria::COUNT | cv::TermCriteria::EPS, it, eps));
  py::array_t<double> o({(py::ssize_t)pts.shape(0), (py::ssize_t)2});
  std::memcpy(o.mutable_data(), dst.data, dst.total() * 16);
  return o;
}
py::array_t<double> project(const py::array_t<double> &X, const py::array_t<double> &K, const py::array_t<double> &D) {
  cv::Mat obj((int)X.shape(0), 1, CV_64FC3, (void *)X.data()), img;
  cv::Mat k(3, 3, CV_64F, (void *)K.data()), d(1, 4, CV_64F, (void *)D.data());
  cv::projectPoints(obj, cv::Mat::zeros(3, 1, CV_64F), cv::Mat::zeros(3, 1, CV_64F), k, d, img);
  py::array_t<double> o({(py::ssize_t)X.shape(0), (py::ssize_t)2});
  std::memcpy(o.mutable_data(), img.data, img.total() * 16);
  return o;
}
py::array_t<uint8_t> resize_nearest(const py::array &img, int w, int h) {
  cv::Mat m = to_mat_u8(img), o;
  cv::resize(m, o, cv::Size(w, h), 0, 0, cv::INTER_NEAREST);
  return from_mat_u8(o);
}
py::tuple moments(const py::array &img) {
  cv::Mat m = to_mat_u8(img);
  auto mo = cv::moments(m, true);
  return py::make_tuple(mo.m00, mo.m10, mo.m01);
}
py::array_t<uint8_t> circles(const py::array &img, const py::array_t<int> &c, int r) {
  cv::Mat m = to_mat_u8(img);
  for (py::ssize_t i = 0; i < c.shape(0); ++i) cv::circle(m, cv::Point(c.at(i, 0), c.at(i, 1)), r, cv::Scalar(0), -1);
  return from_mat_u8(m);
}
py::tuple lk_init(const py::array &a, const py::array &b, const py::array_t<float> &p0, const py::array_t<float> &p1, int win, int lev) {
  cv::Mat A = to_mat_u8(a), Bm = to_mat_u8(b);
  std::vector<cv::Point2f> q0(p0.shape(0)), q1(p0.shape(0));
  for (size_t i = 0; i < q0.size(); ++i) { q0[i] = cv::Point2f(p0.at(i, 0), p0.at(i, 1)); q1[i] = cv::Point2f(p1.at(i, 0), p1.at(i, 1)); }
  std::vector<uchar> st;
  std::vector<float> err;
  cv::calcOpticalFlowPyrLK(A, Bm, q0, q1, st, err, cv::Size(win, win), lev,
                           cv::TermCriteria(cv::TermCriteria::COUNT | cv::TermCriteria::EPS, 20, 0.03), cv::OPTFLOW_USE_INITIAL_FLOW);
  py::array_t<float> o({(py::ssize_t)q1.size(), (py::ssize_t)2});
  py::array_t<uint8_t> s({(py::ssize_t)st.size()});
  for (size_t i = 0; i < q1.size(); ++i) { o.mutable_at(i, 0) = q1[i].x; o.mutable_at(i, 1) = q1[i].y; s.mutable_at(i) = st[i]; }
  return py::make_tuple(o, s);
}
py::array_t<uint8_t> erode_k(const py::array &img, int k) {
  cv::Mat m = to_mat_u8(img), o;
  cv::erode(m, o, cv::Mat::ones(k, k, CV_8U));
  return from_mat_u8(o);
}
}  // namespace cvops
