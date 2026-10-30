// SPDX-License-Identifier: GPL-3.0-or-later
// Minimal JSON writer (stats topic); floats in shortest round-trip form like Python's json.dumps, NaN -> null.
#pragma once

#include <charconv>
#include <cmath>
#include <string>

namespace savior {

class JsonWriter {
 public:
  JsonWriter &begin_obj() { sep(); s_ += '{'; first_ = true; return *this; }
  JsonWriter &end_obj() { s_ += '}'; first_ = false; return *this; }
  JsonWriter &begin_arr() { sep(); s_ += '['; first_ = true; return *this; }
  JsonWriter &end_arr() { s_ += ']'; first_ = false; return *this; }
  JsonWriter &key(const std::string &k) {
    sep();
    str_(k);
    s_ += ": ";
    first_ = true;  // the value follows without a separator
    return *this;
  }
  JsonWriter &val(double v) {
    sep();
    if (!std::isfinite(v)) { s_ += std::isnan(v) ? "null" : (v > 0 ? "Infinity" : "-Infinity"); return *this; }
    char buf[64];
    auto r = std::to_chars(buf, buf + sizeof(buf), v);
    std::string t(buf, r.ptr);
    if (t.find_first_of(".eEn") == std::string::npos) t += ".0";
    s_ += t;
    return *this;
  }
  JsonWriter &val(int v) { sep(); s_ += std::to_string(v); return *this; }
  JsonWriter &val(long v) { sep(); s_ += std::to_string(v); return *this; }
  JsonWriter &val(bool v) { sep(); s_ += v ? "true" : "false"; return *this; }
  JsonWriter &val(const std::string &v) { sep(); str_(v); return *this; }
  JsonWriter &val(const char *v) { sep(); str_(v); return *this; }
  JsonWriter &null() { sep(); s_ += "null"; return *this; }
  JsonWriter &raw(const std::string &r) { sep(); s_ += r; return *this; }
  const std::string &str() const { return s_; }

 private:
  void sep() {
    if (!first_) s_ += ", ";
    first_ = false;
  }
  void str_(const std::string &v) {
    s_ += '"';
    for (char c : v) {
      if (c == '"' || c == '\\') { s_ += '\\'; s_ += c; }
      else if ((unsigned char)c < 0x20) { char b[8]; std::snprintf(b, sizeof(b), "\\u%04x", c); s_ += b; }
      else s_ += c;
    }
    s_ += '"';
  }
  std::string s_;
  bool first_ = true;
};

}  // namespace savior
