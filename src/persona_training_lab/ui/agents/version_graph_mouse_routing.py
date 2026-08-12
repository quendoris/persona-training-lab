from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent

from persona_training_lab.ui.agents.version_graph_action_menu_policy import (
    VersionGraphCanvas as ActionMenuPolicyVersionGraphCanvas,
)
from persona_training_lab.ui.keybindings.definitions import (
    agent_graph_mouse_bindings_by_id,
)
from persona_training_lab.ui.keybindings.manager import MouseBindingValue


def _mapped_mouse_event(
    source: QMouseEvent,
    *,
    button: Qt.MouseButton | None = None,
    buttons: Qt.MouseButton | None = None,
    modifiers: Qt.KeyboardModifier | None = None,
) -> QMouseEvent:
    """Clone a mouse event while replacing only canonical routing state."""

    mapped = QMouseEvent(
        source.type(),
        source.position(),
        source.scenePosition(),
        source.globalPosition(),
        source.button() if button is None else button,
        source.buttons() if buttons is None else buttons,
        source.modifiers() if modifiers is None else modifiers,
        source.pointingDevice(),
    )
    mapped.setAccepted(source.isAccepted())
    return mapped


def _sync_mouse_event_acceptance(
    source: QMouseEvent,
    mapped: QMouseEvent,
) -> None:
    source.setAccepted(mapped.isAccepted())


class VersionGraphCanvas(ActionMenuPolicyVersionGraphCanvas):
    """Route configurable mouse gestures onto stable graph interactions."""

    _MOUSE_BUTTONS = {
        "left": Qt.MouseButton.LeftButton,
        "right": Qt.MouseButton.RightButton,
        "middle": Qt.MouseButton.MiddleButton,
        "back": Qt.MouseButton.BackButton,
        "forward": Qt.MouseButton.ForwardButton,
    }
    _MOUSE_MODIFIERS = {
        "none": Qt.KeyboardModifier.NoModifier,
        "shift": Qt.KeyboardModifier.ShiftModifier,
        "control": Qt.KeyboardModifier.ControlModifier,
        "alt": Qt.KeyboardModifier.AltModifier,
        "meta": Qt.KeyboardModifier.MetaModifier,
    }
    _RELEVANT_MODIFIERS = (
        Qt.KeyboardModifier.ShiftModifier
        | Qt.KeyboardModifier.ControlModifier
        | Qt.KeyboardModifier.AltModifier
        | Qt.KeyboardModifier.MetaModifier
    )

    def __init__(self, nodes) -> None:
        self._input_binding_manager = None
        self._input_drag_action: str | None = None
        self._input_actual_button = Qt.MouseButton.NoButton
        self._input_canonical_button = Qt.MouseButton.NoButton
        self._input_close_on_click = False
        self._default_mouse_definitions = agent_graph_mouse_bindings_by_id()
        super().__init__(nodes)

    def set_input_bindings(self, manager) -> None:
        old = self._input_binding_manager
        if old is manager:
            return
        if old is not None:
            try:
                old.bindings_changed.disconnect(self._on_input_bindings_changed)
            except (RuntimeError, TypeError):
                pass
        self._input_binding_manager = manager
        if manager is not None:
            manager.bindings_changed.connect(self._on_input_bindings_changed)
        self._cancel_input_drag()
        self.update()

    def _on_input_bindings_changed(self) -> None:
        self._cancel_input_drag()
        self.unsetCursor()
        self.update()

    def wheelEvent(self, event) -> None:  # noqa: N802
        if not self._wheel_matches("zoom_canvas", event):
            event.ignore()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        action = self._press_action(event)
        if action is None:
            super().mousePressEvent(event)
            return

        canonical_button = self._canonical_button(action)
        self._input_drag_action = action
        self._input_actual_button = event.button()
        self._input_canonical_button = canonical_button
        self._input_close_on_click = (
            self._node_at(event.position()) is None
            and self._mouse_press_matches("close_node_menu", event)
        )
        mapped = _mapped_mouse_event(
            event,
            button=canonical_button,
            buttons=canonical_button,
            modifiers=self._canonical_modifiers(action),
        )
        super().mousePressEvent(mapped)
        _sync_mouse_event_acceptance(event, mapped)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        action = self._input_drag_action
        if action is None:
            super().mouseMoveEvent(event)
            return
        if not event.buttons() & self._input_actual_button:
            super().mouseMoveEvent(event)
            return

        if action == "close_node_menu":
            event.accept()
            return

        canonical_button = self._input_canonical_button
        modifiers = self._canonical_modifiers(action)
        if action in {"move_node", "move_subtree"}:
            if self._mouse_move_matches("move_subtree", event):
                action = "move_subtree"
                modifiers = Qt.KeyboardModifier.ShiftModifier
            elif self._mouse_move_matches("move_node", event):
                action = "move_node"
                modifiers = Qt.KeyboardModifier.NoModifier
            self._input_drag_action = action

        mapped = _mapped_mouse_event(
            event,
            button=Qt.MouseButton.NoButton,
            buttons=canonical_button,
            modifiers=modifiers,
        )
        super().mouseMoveEvent(mapped)
        _sync_mouse_event_acceptance(event, mapped)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        action = self._input_drag_action
        if action is None or event.button() != self._input_actual_button:
            super().mouseReleaseEvent(event)
            return

        canonical_button = self._input_canonical_button
        mapped = _mapped_mouse_event(
            event,
            button=canonical_button,
            buttons=Qt.MouseButton.NoButton,
            modifiers=self._canonical_modifiers(action),
        )
        super().mouseReleaseEvent(mapped)
        _sync_mouse_event_acceptance(event, mapped)
        self._cancel_input_drag()

    def _press_action(self, event: QMouseEvent) -> str | None:
        if self._menu_action_at(event.position()) is not None:
            return (
                "open_node_menu"
                if self._mouse_press_matches("open_node_menu", event)
                else None
            )

        node_id = self._node_at(event.position())
        if node_id is not None:
            for binding_id in (
                "move_subtree",
                "move_node",
                "open_node_menu",
            ):
                if self._mouse_press_matches(binding_id, event):
                    return binding_id
            return None

        for binding_id in (
            "pan_canvas_primary",
            "pan_canvas_secondary",
            "close_node_menu",
        ):
            if self._mouse_press_matches(binding_id, event):
                return binding_id
        return None

    def _canonical_button(self, action: str):
        if action in {
            "pan_canvas_secondary",
            "move_node",
            "move_subtree",
        }:
            return Qt.MouseButton.RightButton
        return Qt.MouseButton.LeftButton

    @staticmethod
    def _canonical_modifiers(action: str):
        if action == "move_subtree":
            return Qt.KeyboardModifier.ShiftModifier
        return Qt.KeyboardModifier.NoModifier

    def _mouse_press_matches(self, binding_id: str, event: QMouseEvent) -> bool:
        binding = self._mouse_binding(binding_id)
        button = self._MOUSE_BUTTONS.get(binding.button)
        return (
            button is not None
            and event.button() == button
            and self._event_modifier_name(event.modifiers()) == binding.modifier
        )

    def _mouse_move_matches(self, binding_id: str, event: QMouseEvent) -> bool:
        binding = self._mouse_binding(binding_id)
        button = self._MOUSE_BUTTONS.get(binding.button)
        return (
            button is not None
            and bool(event.buttons() & button)
            and self._event_modifier_name(event.modifiers()) == binding.modifier
        )

    def _wheel_matches(self, binding_id: str, event) -> bool:
        binding = self._mouse_binding(binding_id)
        return (
            binding.button == "wheel"
            and self._event_modifier_name(event.modifiers()) == binding.modifier
        )

    def _mouse_binding(self, binding_id: str) -> MouseBindingValue:
        manager = self._input_binding_manager
        if manager is not None:
            return manager.mouse_binding(binding_id)
        definition = self._default_mouse_definitions[binding_id]
        return MouseBindingValue(definition.button, definition.modifier)

    @classmethod
    def _event_modifier_name(cls, modifiers) -> str:
        relevant = modifiers & cls._RELEVANT_MODIFIERS
        matches = [
            name
            for name, flag in cls._MOUSE_MODIFIERS.items()
            if name != "none" and bool(relevant & flag)
        ]
        if not matches:
            return "none"
        if len(matches) == 1:
            return matches[0]
        return "multiple"

    def _cancel_input_drag(self) -> None:
        self._input_drag_action = None
        self._input_actual_button = Qt.MouseButton.NoButton
        self._input_canonical_button = Qt.MouseButton.NoButton
        self._input_close_on_click = False
