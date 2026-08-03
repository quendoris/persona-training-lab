from __future__ import annotations

import sys

from . import screen_agents_final as _screen_agents_final


AgentsScreen = _screen_agents_final.AgentsScreen

# Keep historical import paths as aliases to the single public screen. New code
# should import AgentsScreen from persona_training_lab.ui.agents directly.
_COMPATIBILITY_SCREEN_MODULES = (
    "screen",
    "screen_locked_layout",
    "screen_stateful",
    "screen_history_diagnostics",
)
for module_name in _COMPATIBILITY_SCREEN_MODULES:
    sys.modules[f"{__name__}.{module_name}"] = _screen_agents_final

__all__ = ["AgentsScreen"]
