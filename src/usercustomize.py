from __future__ import annotations

import importlib
import sys


def _route_agents_screen_to_stateful_lineage() -> None:
    try:
        canvas_module = importlib.import_module("persona_training_lab.ui.agents.screen_stateful")
    except Exception:
        return
    sys.modules["persona_training_lab.ui.agents.screen"] = canvas_module


_route_agents_screen_to_stateful_lineage()
