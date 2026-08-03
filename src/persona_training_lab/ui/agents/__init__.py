from __future__ import annotations

import sys

from . import screen_agents_final as _screen_agents_final
from . import screen_history_diagnostics as _legacy_screen_history_diagnostics
from . import screen_history_diagnostics_compat as _screen_history_diagnostics_compat

# Keep direct legacy imports Qt-enum safe while routing all public screen aliases
# through the final bounded layout and persistent diagnostic layer.
_legacy_screen_history_diagnostics.AgentsScreen.eventFilter = (
    _screen_history_diagnostics_compat.AgentsScreen.eventFilter
)
_legacy_screen_history_diagnostics.AgentsScreen._qt_numeric_value = (
    _screen_history_diagnostics_compat.AgentsScreen.__dict__["_qt_numeric_value"]
)
_legacy_screen_history_diagnostics.AgentsScreen._event_type_name = (
    _screen_history_diagnostics_compat.AgentsScreen.__dict__["_event_type_name"]
)

AgentsScreen = _screen_agents_final.AgentsScreen
sys.modules[__name__ + ".screen"] = _screen_agents_final
sys.modules[__name__ + ".screen_locked_layout"] = _screen_agents_final
sys.modules[__name__ + ".screen_stateful"] = _screen_agents_final
sys.modules[__name__ + ".screen_history_diagnostics"] = _screen_agents_final

__all__ = ["AgentsScreen"]
