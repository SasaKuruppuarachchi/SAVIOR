"""Optional colorama shim (port addition, see PORTING.md).

Uses the real ``colorama`` package when installed; otherwise provides no-op
``init`` and an empty-string ``Fore`` so that the ported code has no hard
dependency on colorama. Colouring is disabled when RPG_NO_COLOR is set.
"""
import os

try:
    if os.environ.get('RPG_NO_COLOR'):
        raise ImportError
    from colorama import init, Fore  # noqa: F401
except ImportError:  # pragma: no cover - trivial
    def init(*args, **kwargs):
        return None

    class _NoColor(object):
        def __getattr__(self, name):
            return ''

    Fore = _NoColor()
