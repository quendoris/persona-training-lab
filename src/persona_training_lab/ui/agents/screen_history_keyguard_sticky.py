from __future__ import annotations

# Compatibility import for older code paths. Sticky modifier behaviour belongs
# to the semantic history transport layer; this module adds no MRO layer.
from persona_training_lab.ui.agents.screen_history_transport import AgentsScreen


__all__ = ["AgentsScreen"]
