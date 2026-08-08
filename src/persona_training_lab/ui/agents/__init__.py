from __future__ import annotations

import sys

from . import screen_workspace_composition as _screen_workspace_composition


AgentsScreen = _screen_workspace_composition.AgentsScreen

# Historical public screen implementations now resolve to the single composed
# workspace. Internal architectural layers use explicit module names instead.
_COMPATIBILITY_SCREEN_MODULES = (
    "screen",
    "screen_canvas",
    "screen_tree_canvas",
    "screen_layout",
    "screen_locked_layout",
    "screen_history_diagnostics",
)
for module_name in _COMPATIBILITY_SCREEN_MODULES:
    sys.modules[f"{__name__}.{module_name}"] = _screen_workspace_composition

__all__ = ["AgentsScreen"]
