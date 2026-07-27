from __future__ import annotations

import sys

from . import screen_history_diagnostics as _screen_history_diagnostics

AgentsScreen = _screen_history_diagnostics.AgentsScreen
sys.modules[__name__ + ".screen"] = _screen_history_diagnostics
sys.modules[__name__ + ".screen_locked_layout"] = _screen_history_diagnostics
sys.modules[__name__ + ".screen_stateful"] = _screen_history_diagnostics

__all__ = ["AgentsScreen"]
