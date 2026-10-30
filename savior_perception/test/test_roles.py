# SPDX-License-Identifier: GPL-3.0-or-later
import os

import pytest

from conftest import PKG_ROOT
from savior_perception.core.roles import RoleTable


def test_default_roles_file():
    rt = RoleTable.from_yaml(os.path.join(PKG_ROOT, "config", "roles_default.yaml"))
    assert rt.role("person") == "dynamic"
    assert rt.role("Chair ") == "potential"
    assert rt.role("tv") == "ignore"
    assert rt.half_extent("car", 0.35) == 1.5 and rt.half_extent("person", 0.35) == 0.35
    assert "person" in rt.relevant_classes() and "chair" in rt.relevant_classes()


def test_warehouse_profile():
    rt = RoleTable.from_dict({"dynamic": ["person"], "potential": ["forklift", "box", "pallet", "trolley"],
                              "static": ["rack", "guard_rail", "window"], "default": "static"})
    assert rt.role("rack") == "static" and rt.role("unknown") == "static" and rt.role("box") == "potential"


def test_invalid():
    with pytest.raises(ValueError):
        RoleTable.from_dict({"dynamic": ["person"], "potential": ["person"]})
    with pytest.raises(ValueError):
        RoleTable.from_dict({"default": "maybe"})
    with pytest.raises(ValueError):
        RoleTable.from_dict({"dynamics": ["person"]})
