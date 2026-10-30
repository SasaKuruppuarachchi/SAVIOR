// SPDX-License-Identifier: GPL-3.0-or-later
#include "savior_cpp/roles.hpp"

#include <algorithm>
#include <set>
#include <stdexcept>

#include <yaml-cpp/yaml.h>

namespace savior {

std::string norm_name(const std::string &s) {
  size_t a = 0, b = s.size();
  while (a < b && std::isspace((unsigned char)s[a])) ++a;
  while (b > a && std::isspace((unsigned char)s[b - 1])) --b;
  std::string o = s.substr(a, b - a);
  std::transform(o.begin(), o.end(), o.begin(), [](unsigned char c) { return std::tolower(c); });
  return o;
}

RoleTable::RoleTable() {}

void RoleTable::add(Role role, const std::string &name) {
  const std::string k = norm_name(name);
  auto it = roles_.find(k);
  if (it != roles_.end() && it->second != role)
    throw std::invalid_argument("class '" + name + "' listed as both '" + role_name(it->second) + "' and '" +
                                role_name(role) + "'");
  roles_[k] = role;
}

RoleTable RoleTable::from_yaml(const std::string &path) {
  YAML::Node d = YAML::LoadFile(path);
  RoleTable t;
  static const std::set<std::string> allowed = {"dynamic", "potential", "static", "ignore", "default", "half_extent_m"};
  if (d && d.IsMap()) {
    for (auto it : d) {
      const std::string k = it.first.as<std::string>();
      if (!allowed.count(k)) throw std::invalid_argument("unknown keys in role table: " + k);
    }
    for (const char *r : {"dynamic", "potential", "static", "ignore"}) {
      if (d[r] && d[r].IsSequence())
        for (auto n : d[r]) t.add(role_from_name(r), n.as<std::string>());
    }
    if (d["default"]) t.default_role = role_from_name(d["default"].as<std::string>());
    if (d["half_extent_m"] && d["half_extent_m"].IsMap())
      for (auto it : d["half_extent_m"]) {
        double v = it.second.as<double>();
        if (v < 0) throw std::invalid_argument("half_extent_m must be >= 0");
        t.half_extent_m[norm_name(it.first.as<std::string>())] = v;
      }
  }
  return t;
}

Role RoleTable::role(const std::string &cls) const {
  auto it = roles_.find(norm_name(cls));
  return it == roles_.end() ? default_role : it->second;
}

double RoleTable::half_extent(const std::string &cls, double def) const {
  auto it = half_extent_m.find(norm_name(cls));
  return it == half_extent_m.end() ? def : it->second;
}

std::vector<std::string> RoleTable::classes_with_role(Role r) const {
  std::vector<std::string> o;
  for (auto &kv : roles_)
    if (kv.second == r) o.push_back(kv.first);
  std::sort(o.begin(), o.end());
  return o;
}

std::vector<std::string> RoleTable::relevant_classes() const {
  auto a = classes_with_role(Role::Dynamic);
  auto b = classes_with_role(Role::Potential);
  a.insert(a.end(), b.begin(), b.end());
  return a;
}

std::string RoleTable::repr() const {
  auto j = [](const std::vector<std::string> &v) {
    std::string s = "[";
    for (size_t i = 0; i < v.size(); ++i) s += (i ? ", '" : "'") + v[i] + "'";
    return s + "]";
  };
  return "RoleTable(dynamic=" + j(classes_with_role(Role::Dynamic)) + ", potential=" +
         j(classes_with_role(Role::Potential)) + ", static=" + j(classes_with_role(Role::Static)) +
         ", default=" + role_name(default_role) + ")";
}

}  // namespace savior
