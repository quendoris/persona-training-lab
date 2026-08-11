from __future__ import annotations

# Compatibility import for historical code paths. The live implementation now
# resides in screen_history_transport and no longer defines a KeyGuard layer.
from persona_training_lab.ui.agents.screen_history_transport import AgentsScreen


__all__ = ["AgentsScreen"]
