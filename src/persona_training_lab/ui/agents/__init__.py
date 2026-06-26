from __future__ import annotations

import sys

from . import screen_stateful_fixed as _screen_stateful_fixed

AgentsScreen = _screen_stateful_fixed.AgentsScreen
sys.modules[__name__ + ".screen"] = _screen_stateful_fixed
sys.modules[__name__ + ".screen_locked_layout"] = _screen_stateful_fixed
sys.modules[__name__ + ".screen_stateful"] = _screen_stateful_fixed

__all__ = ["AgentsScreen"]
