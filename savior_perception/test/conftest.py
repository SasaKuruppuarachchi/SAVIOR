# SPDX-License-Identifier: GPL-3.0-or-later
import os
import sys

import pytest

PKG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

# OpenVINS example calibrations: $SAVIOR_OV_CONFIG, else <ws>/ref/open_vins/config if present, else the fork in this repo.
_WS = os.environ.get("SAVIOR_WS", os.path.abspath(os.path.join(PKG_ROOT, "..", "..", "..")))
_REF = os.path.join(_WS, "ref", "open_vins", "config")
REF_CONFIG = os.environ.get("SAVIOR_OV_CONFIG") or (
    _REF if os.path.isdir(_REF) else os.path.join(PKG_ROOT, "..", "open_vins", "config"))
EUROC = os.path.join(REF_CONFIG, "euroc_mav", "kalibr_imucam_chain.yaml")
T265 = os.path.join(REF_CONFIG, "rs_t265", "kalibr_imucam_chain.yaml")


def calib_path(name):
    p = {"euroc": EUROC, "t265": T265}[name]
    if not os.path.exists(p):
        pytest.skip(f"example calibration not found: {p}")
    return p
