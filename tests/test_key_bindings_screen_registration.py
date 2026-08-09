from __future__ import annotations

from persona_training_lab.ui.i18n.text import text
from persona_training_lab.ui.keybindings.screen import KeyBindingsScreen
from persona_training_lab.ui.panels.inspector_panel import INSPECTOR_CONTEXT_IDS
from persona_training_lab.ui.shell.app_sidebar import APPLICATION_NAV_ITEMS


def test_key_bindings_screen_is_exposed_in_application_navigation() -> None:
    items = {
        screen_id: (icon, title_key)
        for screen_id, icon, title_key in APPLICATION_NAV_ITEMS
    }

    assert items["keybindings"] == ("КЛ", "nav.keybindings")
    assert text(None, items["keybindings"][1]) == "Назначения клавиш"
    assert KeyBindingsScreen.__name__ == "KeyBindingsScreen"


def test_key_bindings_screen_has_dedicated_inspector_context() -> None:
    assert "keybindings" in INSPECTOR_CONTEXT_IDS

    prefix = "inspector.context.keybindings"
    assert text(None, f"{prefix}.title") == "Назначения клавиш"
    assert "без перезапуска" in text(None, f"{prefix}.next")

    checks = tuple(
        text(None, f"{prefix}.check.{index}")
        for index in range(1, 5)
    )
    assert len(checks) == 4
    assert all(check for check in checks)
