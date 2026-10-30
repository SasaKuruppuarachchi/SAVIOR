# SPDX-License-Identifier: GPL-3.0-or-later
"""Helpers shared by the Isaac Sim scripts (import AFTER SimulationApp has been created, except the constants)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                       # savior_datasets/warehouse
if PKG not in sys.path:
    sys.path.insert(0, PKG)

WS = os.path.abspath(os.path.join(PKG, '..', '..', '..', '..'))   # savior_ws
DATA = os.environ.get('SAVIOR_WAREHOUSE_DATA', os.path.join(WS, 'data', 'warehouse'))
ASSET_ROOT = os.environ.get('SAVIOR_ISAAC_ASSETS', '/home/sasa/isaac_sim_assets/Assets/Isaac/6.0')
ANIM_CACHE = os.path.join(DATA, 'cache', 'anims')
IRA_BIPED = 'isaacsim.replicator.agent.core'   # extension holding data/test_scenes/test_biped/biped_demo_meters.usd

from wh.classes import CHARACTERS  # noqa: E402,F401


def asset(path):
    """'Isaac/Props/...' -> absolute path inside the local asset pack; absolute paths are returned unchanged."""
    return path if os.path.isabs(path) else os.path.join(ASSET_ROOT, path)


def char_usd(name):
    return asset(f'Isaac/People/Characters/{name}/{name}.usd')


def start_app(headless=True, extra=None):
    """SimulationApp with the local asset root (no Nucleus / network asset server)."""
    from isaacsim import SimulationApp
    cfg = {'headless': headless, 'renderer': 'RaytracedLighting', 'anti_aliasing': 3}
    cfg.update(extra or {})
    app = SimulationApp(cfg)
    import carb
    s = carb.settings.get_settings()
    for key in ('/persistent/isaac/asset_root/default', '/persistent/isaac/asset_root/cloud',
                '/persistent/isaac/asset_root/nvidia'):
        s.set(key, ASSET_ROOT)
    return app


def render_settings(motion_blur=False):
    import carb
    s = carb.settings.get_settings()
    s.set('/rtx/post/motionblur/enabled', bool(motion_blur))
    s.set('/rtx/post/dof/enabled', False)
    s.set('/rtx/post/histogram/enabled', False)   # no auto exposure: identical, frame-independent exposure L/R
    s.set('/rtx/post/dlss/execMode', 2)           # quality
    s.set('/omni/replicator/captureOnPlay', False)
