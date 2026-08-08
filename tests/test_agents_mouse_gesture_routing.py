from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QPointF, Qt

from persona_training_lab.ui.agents.version_graph_mouse_routing import (
    VersionGraphCanvas,
)
from persona_training_lab.ui.keybindings.manager import MouseBindingValue


class _FakeMouseEvent:
    def __init__(
        self,
        *,
        button=Qt.MouseButton.NoButton,
        buttons=Qt.MouseButton.NoButton,
        modifiers=Qt.KeyboardModifier.NoModifier,
    ) -> None:
        self._button = button
        self._buttons = buttons
        self._modifiers = modifiers

    def button(self):
        return self._button

    def buttons(self):
        return self._buttons

    def modifiers(self):
        return self._modifiers

    def position(self):
        return QPointF(10.0, 20.0)


def test_mouse_modifier_name_requires_one_exact_modifier() -> None:
    assert (
        VersionGraphCanvas._event_modifier_name(
            Qt.KeyboardModifier.NoModifier
        )
        == "none"
    )
    assert (
        VersionGraphCanvas._event_modifier_name(
            Qt.KeyboardModifier.ShiftModifier
        )
        == "shift"
    )
    assert (
        VersionGraphCanvas._event_modifier_name(
            Qt.KeyboardModifier.ControlModifier
        )
        == "control"
    )
    assert (
        VersionGraphCanvas._event_modifier_name(
            Qt.KeyboardModifier.ShiftModifier
            | Qt.KeyboardModifier.ControlModifier
        )
        == "multiple"
    )


def test_mouse_press_matching_uses_configured_button_and_modifier() -> None:
    screen = SimpleNamespace(
        _MOUSE_BUTTONS=VersionGraphCanvas._MOUSE_BUTTONS,
        _mouse_binding=lambda _binding_id: MouseBindingValue(
            "middle",
            "alt",
        ),
        _event_modifier_name=VersionGraphCanvas._event_modifier_name,
    )
    matching = _FakeMouseEvent(
        button=Qt.MouseButton.MiddleButton,
        modifiers=Qt.KeyboardModifier.AltModifier,
    )
    wrong_modifier = _FakeMouseEvent(
        button=Qt.MouseButton.MiddleButton,
        modifiers=Qt.KeyboardModifier.NoModifier,
    )

    assert (
        VersionGraphCanvas._mouse_press_matches(
            screen,
            "move_node",
            matching,
        )
        is True
    )
    assert (
        VersionGraphCanvas._mouse_press_matches(
            screen,
            "move_node",
            wrong_modifier,
        )
        is False
    )


def test_node_press_prefers_subtree_then_node_then_menu() -> None:
    calls: list[str] = []

    def matches(binding_id: str, _event) -> bool:
        calls.append(binding_id)
        return binding_id == "move_subtree"

    screen = SimpleNamespace(
        _menu_action_at=lambda _position: None,
        _node_at=lambda _position: "branch_1",
        _mouse_press_matches=matches,
    )

    action = VersionGraphCanvas._press_action(screen, _FakeMouseEvent())

    assert action == "move_subtree"
    assert calls == ["move_subtree"]


def test_configured_actions_map_to_stable_internal_buttons() -> None:
    screen = SimpleNamespace()

    assert (
        VersionGraphCanvas._canonical_button(screen, "open_node_menu")
        == Qt.MouseButton.LeftButton
    )
    assert (
        VersionGraphCanvas._canonical_button(screen, "pan_canvas_primary")
        == Qt.MouseButton.LeftButton
    )
    assert (
        VersionGraphCanvas._canonical_button(screen, "move_node")
        == Qt.MouseButton.RightButton
    )
    assert (
        VersionGraphCanvas._canonical_button(screen, "move_subtree")
        == Qt.MouseButton.RightButton
    )
    assert (
        VersionGraphCanvas._canonical_modifiers("move_subtree")
        == Qt.KeyboardModifier.ShiftModifier
    )
