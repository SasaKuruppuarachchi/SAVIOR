# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 The SAVIOR authors
"""Class-role table (docs/INTERFACE.md §3.4).

YAML schema::

    dynamic:   [person]                 # always-dynamic (interaction-tree roots)
    potential: [chair, suitcase, cart]  # promoted only through interaction with a dynamic chain
    static:    []                       # never masked (kept for documentation / overlays)
    default: ignore                     # role of classes not listed (any of the four roles)
    # optional: per-class half depth extent [m] used by the promotion size prior
    half_extent_m: {forklift: 1.2, car: 1.5}

Class names are matched case-insensitively after stripping whitespace.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional

import yaml

from .types import ROLE_DYNAMIC, ROLE_IGNORE, ROLE_POTENTIAL, ROLE_STATIC, ROLES

_ALLOWED_KEYS = {"dynamic", "potential", "static", "ignore", "default", "half_extent_m"}


def _norm(name: str) -> str:
    return str(name).strip().lower()


class RoleTable:
    def __init__(self, dynamic: Iterable[str] = (), potential: Iterable[str] = (),
                 static: Iterable[str] = (), ignore: Iterable[str] = (),
                 default: str = ROLE_IGNORE, half_extent_m: Optional[Dict[str, float]] = None):
        if default not in ROLES:
            raise ValueError(f"default role '{default}' not in {ROLES}")
        self.default = default
        self._roles: Dict[str, str] = {}
        for role, names in ((ROLE_DYNAMIC, dynamic), (ROLE_POTENTIAL, potential),
                            (ROLE_STATIC, static), (ROLE_IGNORE, ignore)):
            for n in names or ():
                key = _norm(n)
                if key in self._roles and self._roles[key] != role:
                    raise ValueError(f"class '{n}' listed as both '{self._roles[key]}' and '{role}'")
                self._roles[key] = role
        self.half_extent_m = {_norm(k): float(v) for k, v in (half_extent_m or {}).items()}
        for k, v in self.half_extent_m.items():
            if v < 0:
                raise ValueError(f"half_extent_m[{k}] must be >= 0")

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "RoleTable":
        d = dict(d or {})
        unknown = set(d) - _ALLOWED_KEYS
        if unknown:
            raise ValueError(f"unknown keys in role table: {sorted(unknown)}")
        return cls(dynamic=d.get("dynamic") or (), potential=d.get("potential") or (),
                   static=d.get("static") or (), ignore=d.get("ignore") or (),
                   default=d.get("default", ROLE_IGNORE), half_extent_m=d.get("half_extent_m"))

    @classmethod
    def from_yaml(cls, path: str) -> "RoleTable":
        with open(path, "r") as fh:
            return cls.from_dict(yaml.safe_load(fh))

    def role(self, cls_name: str) -> str:
        return self._roles.get(_norm(cls_name), self.default)

    def half_extent(self, cls_name: str, default: float) -> float:
        return self.half_extent_m.get(_norm(cls_name), default)

    def classes_with_role(self, role: str):
        return sorted(k for k, r in self._roles.items() if r == role)

    def relevant_classes(self):
        """Classes that can ever be masked (dynamic + potential)."""
        return self.classes_with_role(ROLE_DYNAMIC) + self.classes_with_role(ROLE_POTENTIAL)

    def __repr__(self):
        return (f"RoleTable(dynamic={self.classes_with_role(ROLE_DYNAMIC)}, "
                f"potential={self.classes_with_role(ROLE_POTENTIAL)}, "
                f"static={self.classes_with_role(ROLE_STATIC)}, default={self.default})")
