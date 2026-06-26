from __future__ import annotations

import importlib
import sys


def _route_agents_screen_to_canvas() -> None:
    try:
        curved_graph_module = importlib.import_module("persona_training_lab.ui.agents.version_graph_curved")
        sys.modules["persona_training_lab.ui.agents.version_graph_canvas"] = curved_graph_module
        canvas_module = importlib.import_module("persona_training_lab.ui.agents.screen_tree_canvas")
    except Exception:
        return
    sys.modules["persona_training_lab.ui.agents.screen"] = canvas_module


_route_agents_screen_to_canvas()
