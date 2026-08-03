from __future__ import annotations

from math import ceil

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QMouseEvent

from persona_training_lab.ui.agents.version_graph_clean_layout import (
    VersionGraphCanvas as CleanLayoutVersionGraphCanvas,
)
from persona_training_lab.ui.agents.version_graph_workspace import (
    WorkspaceBounds,
    WorkspaceGeometry,
    build_workspace_geometry,
    grow_workspace_geometry,
)
from persona_training_lab.ui.keybindings.definitions import (
    agent_graph_mouse_bindings_by_id,
)
from persona_training_lab.ui.keybindings.manager import MouseBindingValue


class _MappedMouseEvent:
    """Delegate a Qt mouse event while overriding routing fields for the graph."""

    def __init__(
        self,
        source,
        *,
        button=None,
        buttons=None,
        modifiers=None,
    ) -> None:
        self._source = source
        self._button = button
        self._buttons = buttons
        self._modifiers = modifiers

    def button(self):
        return self._source.button() if self._button is None else self._button

    def buttons(self):
        return self._source.buttons() if self._buttons is None else self._buttons

    def modifiers(self):
        return (
            self._source.modifiers()
            if self._modifiers is None
            else self._modifiers
        )

    def __getattr__(self, name):
        return getattr(self._source, name)


class VersionGraphCanvas(CleanLayoutVersionGraphCanvas):
    """Size workspace dynamically and route configurable mouse gestures."""

    workspace_origin_shifted = Signal(QPointF)

    _HORIZONTAL_MARGIN = 1800.0
    _VERTICAL_MARGIN = 1100.0
    _MINIMUM_WORKSPACE_WIDTH = 3200.0
    _MINIMUM_WORKSPACE_HEIGHT = 2400.0
    _ROW_GAP = 52.0

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
        self._workspace_geometry: WorkspaceGeometry | None = None
        self._input_binding_manager = None
        self._input_drag_action: str | None = None
        self._input_actual_button = Qt.MouseButton.NoButton
        self._input_canonical_button = Qt.MouseButton.NoButton
        self._input_close_on_click = False
        self._default_mouse_definitions = agent_graph_mouse_bindings_by_id()
        super().__init__(nodes)
        # Persistent offsets are loaded inside the parent constructor, after the
        # first QWidget size pass, so rebuild once more with the real saved state.
        self._rebuild_workspace_geometry(emit_shift=False)

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

    def set_nodes(self, nodes) -> None:
        self._workspace_geometry = None
        super().set_nodes(nodes)

    def toggle_flipped(self) -> None:
        super().toggle_flipped()
        self._rebuild_workspace_geometry()

    def restore_layout_snapshot(self, snapshot) -> None:
        super().restore_layout_snapshot(snapshot)
        self._rebuild_workspace_geometry()

    def reset_layout(self) -> None:
        super().reset_layout()
        self._rebuild_workspace_geometry()

    def reset_node_layout(self, node_id: str) -> None:
        super().reset_node_layout(node_id)
        self._rebuild_workspace_geometry()

    def reset_subtree_layout(self, node_id: str) -> None:
        super().reset_subtree_layout(node_id)
        self._rebuild_workspace_geometry()

    def forget_layout_nodes(self, node_ids) -> None:
        super().forget_layout_nodes(node_ids)
        self._rebuild_workspace_geometry()

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
        mapped = _MappedMouseEvent(
            event,
            button=canonical_button,
            buttons=canonical_button,
            modifiers=self._canonical_modifiers(action),
        )
        super().mousePressEvent(mapped)

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

        mapped = _MappedMouseEvent(
            event,
            button=Qt.MouseButton.NoButton,
            buttons=canonical_button,
            modifiers=modifiers,
        )
        super().mouseMoveEvent(mapped)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        action = self._input_drag_action
        if action is None or event.button() != self._input_actual_button:
            super().mouseReleaseEvent(event)
            self._rebuild_workspace_geometry()
            return

        canonical_button = self._input_canonical_button
        mapped = _MappedMouseEvent(
            event,
            button=canonical_button,
            buttons=Qt.MouseButton.NoButton,
            modifiers=self._canonical_modifiers(action),
        )
        super().mouseReleaseEvent(mapped)
        self._cancel_input_drag()
        self._rebuild_workspace_geometry()

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

    def _move_nodes(self, node_ids: tuple[str, ...], delta: QPointF) -> None:
        before = tuple(
            (node_id, self._node_offsets.get(node_id, QPointF()))
            for node_id in node_ids
        )
        super()._move_nodes(node_ids, delta)
        after = tuple(
            (node_id, self._node_offsets.get(node_id, QPointF()))
            for node_id in node_ids
        )
        if before != after:
            self._grow_workspace_to_current_content()

    def _refresh_size(self) -> None:
        self._ensure_workspace_geometry()
        self._apply_workspace_size()

    def _canvas_width(self) -> int:
        geometry = self._ensure_workspace_geometry()
        return max(1, int(ceil(geometry.width * self._zoom)))

    def _canvas_height(self) -> int:
        geometry = self._ensure_workspace_geometry()
        return max(1, int(ceil(geometry.height * self._zoom)))

    def _positions(self) -> dict[str, tuple[float, float]]:
        geometry = self._ensure_workspace_geometry()
        return {
            node_id: (
                (x + geometry.origin_x) * self._zoom,
                (y + geometry.origin_y) * self._zoom,
            )
            for node_id, (x, y) in self._raw_positions().items()
        }

    def _raw_positions(self) -> dict[str, tuple[float, float]]:
        lanes = self._lanes()
        lane_offsets = self._lane_offsets(lanes)
        levels = self._display_levels()
        max_level = max(levels.values(), default=0)
        result: dict[str, tuple[float, float]] = {}
        for node in self._nodes:
            level = levels.get(node.node_id, self._level(node))
            visual_level = max_level - level if self._flipped else level
            offset = self._node_offsets.get(node.node_id, QPointF())
            offset_y = -offset.y() if self._flipped else offset.y()
            result[node.node_id] = (
                lane_offsets.get(lanes.get(node.node_id, 0), 0.0) + offset.x(),
                visual_level * self._ROW_GAP + offset_y,
            )
        return result

    def _content_bounds(self) -> WorkspaceBounds:
        positions = self._raw_positions()
        if not positions:
            return WorkspaceBounds(-60.0, -60.0, 60.0, 60.0)

        by_id = {node.node_id: node for node in self._nodes}
        left = float("inf")
        top = float("inf")
        right = float("-inf")
        bottom = float("-inf")
        for node_id, (x, y) in positions.items():
            node = by_id.get(node_id)
            label_width = (
                self._label_width(node.title) if node is not None else 120.0
            )
            left = min(left, x - 34.0)
            top = min(top, y - 34.0)
            right = max(
                right,
                x + 28.0 + max(64.0, label_width + 28.0),
            )
            bottom = max(bottom, y + 34.0)
        return WorkspaceBounds(left, top, right, bottom)

    def _ensure_workspace_geometry(self) -> WorkspaceGeometry:
        if self._workspace_geometry is None:
            self._workspace_geometry = build_workspace_geometry(
                self._content_bounds(),
                horizontal_margin=self._HORIZONTAL_MARGIN,
                vertical_margin=self._VERTICAL_MARGIN,
                minimum_width=self._MINIMUM_WORKSPACE_WIDTH,
                minimum_height=self._MINIMUM_WORKSPACE_HEIGHT,
            )
        return self._workspace_geometry

    def _rebuild_workspace_geometry(self, *, emit_shift: bool = True) -> None:
        old = self._workspace_geometry
        new = build_workspace_geometry(
            self._content_bounds(),
            horizontal_margin=self._HORIZONTAL_MARGIN,
            vertical_margin=self._VERTICAL_MARGIN,
            minimum_width=self._MINIMUM_WORKSPACE_WIDTH,
            minimum_height=self._MINIMUM_WORKSPACE_HEIGHT,
        )
        self._workspace_geometry = new
        self._apply_workspace_size()
        if old is not None and emit_shift:
            delta = QPointF(
                (new.origin_x - old.origin_x) * self._zoom,
                (new.origin_y - old.origin_y) * self._zoom,
            )
            if abs(delta.x()) > 0.5 or abs(delta.y()) > 0.5:
                self.workspace_origin_shifted.emit(delta)

    def _grow_workspace_to_current_content(self) -> None:
        geometry = self._ensure_workspace_geometry()
        grown = grow_workspace_geometry(
            geometry,
            self._content_bounds(),
            horizontal_margin=self._HORIZONTAL_MARGIN,
            vertical_margin=self._VERTICAL_MARGIN,
        )
        if grown != geometry:
            self._workspace_geometry = grown
            self._apply_workspace_size()

    def _apply_workspace_size(self) -> None:
        width = self._canvas_width()
        height = self._canvas_height()
        if self.minimumWidth() != width or self.minimumHeight() != height:
            self.setMinimumSize(width, height)
        if self.width() != width or self.height() != height:
            self.resize(width, height)
        self.updateGeometry()
        self.update()
