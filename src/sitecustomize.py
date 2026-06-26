from __future__ import annotations

import importlib
import sys


def _route_agents_screen_to_canvas() -> None:
    try:
        canvas_module = importlib.import_module("persona_training_lab.ui.agents.screen_locked_layout")
    except Exception:
        return
    sys.modules["persona_training_lab.ui.agents.screen"] = canvas_module


_route_agents_screen_to_canvas()
