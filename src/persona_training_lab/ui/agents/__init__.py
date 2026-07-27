from __future__ import annotations

import sys

from . import screen_history_keyguard_sticky as _screen_history_keyguard_sticky

AgentsScreen = _screen_history_keyguard_sticky.AgentsScreen
sys.modules[__name__ + ".screen"] = _screen_history_keyguard_sticky
sys.modules[__name__ + ".screen_locked_layout"] = _screen_history_keyguard_sticky
sys.modules[__name__ + ".screen_stateful"] = _screen_history_keyguard_sticky

__all__ = ["AgentsScreen"]
