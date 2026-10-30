// SPDX-License-Identifier: GPL-3.0-or-later
// C++ port of savior_perception/core/roles.py (class-role table, docs/INTERFACE.md 3.4).
#pragma once

#include <map>
#include <string>
#include <vector>

#include "savior_cpp/types.hpp"

namespace savior {

class RoleTable {
 public:
  RoleTable();  // default: dynamic = [person], default role ignore
  static RoleTable from_yaml(const std::string &path);
  void add(Role role, const std::string &name);
  Role role(const std::string &cls) const;
  double half_extent(const std::string &cls, double def) const;
  std::vector<std::string> classes_with_role(Role r) const;  // sorted
  std::vector<std::string> relevant_classes() const;         // dynamic + potential
  std::string repr() const;
  Role default_role = Role::Ignore;
  std::map<std::string, double> half_extent_m;

 private:
  std::map<std::string, Role> roles_;
};

std::string norm_name(const std::string &s);  // strip + lower

}  // namespace savior
