from __future__ import annotations

from persona_training_lab.ui.keybindings.screen import KeyBindingsScreen
from persona_training_lab.ui.panels.inspector_panel import INSPECTOR_CONTEXTS
from persona_training_lab.ui.shell.app_sidebar import APPLICATION_NAV_ITEMS


def test_key_bindings_screen_is_exposed_in_application_navigation() -> None:
    items = {screen_id: (icon, title) for screen_id, icon, title in APPLICATION_NAV_ITEMS}

    assert items["keybindings"] == ("КЛ", "Назначения клавиш")
    assert KeyBindingsScreen.__name__ == "KeyBindingsScreen"


def test_key_bindings_screen_has_dedicated_inspector_context() -> None:
    context = INSPECTOR_CONTEXTS["keybindings"]

    assert context.title == "Назначения клавиш"
    assert "без перезапуска" in context.next_action
    assert len(context.checks) == 4
