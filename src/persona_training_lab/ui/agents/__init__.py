from __future__ import annotations

import sys

from . import screen_stateful as _screen_stateful

AgentsScreen = _screen_stateful.AgentsScreen
sys.modules[__name__ + ".screen"] = _screen_stateful
sys.modules[__name__ + ".screen_locked_layout"] = _screen_stateful

__all__ = ["AgentsScreen"]
