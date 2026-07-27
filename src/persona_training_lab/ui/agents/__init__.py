from __future__ import annotations

import sys

from . import screen_history_diagnostics_compat as _screen_history_diagnostics_compat

AgentsScreen = _screen_history_diagnostics_compat.AgentsScreen
sys.modules[__name__ + ".screen"] = _screen_history_diagnostics_compat
sys.modules[__name__ + ".screen_locked_layout"] = _screen_history_diagnostics_compat
sys.modules[__name__ + ".screen_stateful"] = _screen_history_diagnostics_compat

__all__ = ["AgentsScreen"]
