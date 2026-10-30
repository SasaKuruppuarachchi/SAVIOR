# SPDX-License-Identifier: GPL-3.0-or-later
import os

import pytest
import yaml

from conftest import PKG_ROOT
from savior_perception.core.config import PipelineConfig
from savior_perception.params import all_defaults


def _flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, key + "."))
        else:
            out[key] = v
    return out


def test_default_yaml_matches_code():
    with open(os.path.join(PKG_ROOT, "config", "default.yaml")) as fh:
        y = yaml.safe_load(fh)["savior_node"]["ros__parameters"]
    flat = _flatten(y)
    code = all_defaults()
    assert set(flat) == set(code), (set(flat) ^ set(code))
    for k, v in code.items():
        assert flat[k] == v and type(flat[k]) is type(v), (k, flat[k], v)


def test_from_flat_coercion_and_validation():
    c = PipelineConfig.from_flat({"depth.downsample": 1.0, "gating.k_sigma": 2, "tracker.enable": "false"})
    assert c.depth.downsample == 1 and isinstance(c.gating.k_sigma, float) and c.tracker.enable is False
    with pytest.raises(KeyError):
        PipelineConfig.from_flat({"depth.nope": 1})
    with pytest.raises(ValueError):
        PipelineConfig.from_flat({"gating.mode": "magic"})
    nested = PipelineConfig.from_nested({"extension": {"min_px": 4, "max_px": 10}})
    assert nested.extension.min_px == 4
