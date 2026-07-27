from __future__ import annotations

import sys

from . import screen_history_keyguard as _screen_history_keyguard

AgentsScreen = _screen_history_keyguard.AgentsScreen
sys.modules[__name__ + ".screen"] = _screen_history_keyguard
sys.modules[__name__ + ".screen_locked_layout"] = _screen_history_keyguard
sys.modules[__name__ + ".screen_stateful"] = _screen_history_keyguard

__all__ = ["AgentsScreen"]
