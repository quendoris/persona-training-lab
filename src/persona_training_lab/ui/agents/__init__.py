from __future__ import annotations

import sys

from . import screen_history_diagnostics as _legacy_screen_history_diagnostics
from . import screen_history_diagnostics_compat as _screen_history_diagnostics_compat

# Some bootstrap paths import screen_history_diagnostics directly. Patch the
# already-loaded legacy class as well as the module alias so every route uses the
# Qt-enum-safe event filter.
_legacy_screen_history_diagnostics.AgentsScreen.eventFilter = (
    _screen_history_diagnostics_compat.AgentsScreen.eventFilter
)
_legacy_screen_history_diagnostics.AgentsScreen._qt_numeric_value = (
    _screen_history_diagnostics_compat.AgentsScreen.__dict__["_qt_numeric_value"]
)
_legacy_screen_history_diagnostics.AgentsScreen._event_type_name = (
    _screen_history_diagnostics_compat.AgentsScreen.__dict__["_event_type_name"]
)

AgentsScreen = _screen_history_diagnostics_compat.AgentsScreen
sys.modules[__name__ + ".screen"] = _screen_history_diagnostics_compat
sys.modules[__name__ + ".screen_locked_layout"] = _screen_history_diagnostics_compat
sys.modules[__name__ + ".screen_stateful"] = _screen_history_diagnostics_compat
sys.modules[__name__ + ".screen_history_diagnostics"] = _screen_history_diagnostics_compat

__all__ = ["AgentsScreen"]
