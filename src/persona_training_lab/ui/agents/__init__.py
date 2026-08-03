from __future__ import annotations

import sys

from . import screen_agents_final as _screen_agents_final


AgentsScreen = _screen_agents_final.AgentsScreen

# Preserve historical import paths without loading any diagnostic implementation.
sys.modules[__name__ + ".screen"] = _screen_agents_final
sys.modules[__name__ + ".screen_locked_layout"] = _screen_agents_final
sys.modules[__name__ + ".screen_stateful"] = _screen_agents_final
sys.modules[__name__ + ".screen_history_diagnostics"] = _screen_agents_final

__all__ = ["AgentsScreen"]
