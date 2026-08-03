from __future__ import annotations

# Compatibility import for older code paths. The sticky modifier behaviour now
# lives directly in screen_history_keyguard, so this module adds no MRO layer.
from persona_training_lab.ui.agents.screen_history_keyguard import AgentsScreen


__all__ = ["AgentsScreen"]
