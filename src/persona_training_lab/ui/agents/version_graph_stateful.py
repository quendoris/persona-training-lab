from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPaintEvent, QPen

from persona_training_lab.ui.agents.version_graph_locked import VersionGraphCanvas as LockableVersionGraphCanvas
from persona_training_lab.ui.viewmodels.agents import VersionNodeView


class VersionGraphCanvas(LockableVersionGraphCanvas):
    menu_action_requested = Signal(str, str)

    def __init__(self, nodes: tuple[VersionNodeView, ...]) -> None:
        super().__init__(nodes)
        self._menu_node_id: str | None = None
        self._menu_press_action: str | None = None

    def set_nodes(self, nodes: tuple[VersionNodeView, ...]) -> None:
        self._nodes = nodes
        ids = {node.node_id for node in nodes}
        if self._selected_node_id not in ids:
            self._selected_node_id = self.current_node_id()
        if self._menu_node_id not in ids:
            self._menu_node_id = None
        self._hit_rects.clear()
        self._refresh_size()
        self.updateGeometry()
        self.update()

    def reset_node_layout(self, node_id: str) -> None:
        self._node_offsets.pop(node_id, None)
        self._save_offsets()
        self.update()

    def reset_subtree_layout(self, node_id: str) -> None:
        for target_id in self._subtree_node_ids(node_id):
            self._node_offsets.pop(target_id, None)
        self._save_offsets()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        super().paintEvent(event)
        self._draw_canvas_menu()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            action = self._menu_action_at(event.position())
            if action is not None:
                self._press_global_pos = event.globalPosition()
                self._last_global_pos = event.globalPosition()
                self._dragging = False
                self._drag_mode = "menu_action"
                self._menu_press_action = action
                event.accept()
                return

            node_id = self._node_at(event.position())
            self._press_global_pos = event.globalPosition()
            self._last_global_pos = event.globalPosition()
            self._dragging = False
            self._menu_press_action = None
            if node_id is None:
                self._drag_mode = "left_pan"
                self._drag_node_id = None
                self._drag_target_ids = ()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self._drag_mode = "left_node_click"
                self._drag_node_id = node_id
                self._drag_target_ids = ()
                self._selected_node_id = node_id
                self.node_selected.emit(node_id)
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                self.update()
            event.accept()
            return

        if event.button() == Qt.MouseButton.RightButton:
            node_id = self._node_at(event.position())
            self._press_global_pos = event.globalPosition()
            self._last_global_pos = event.globalPosition()
            self._dragging = False
            self._menu_press_action = None
            if node_id is None:
                self._drag_mode = "right_pan"
                self._drag_node_id = None
                self._drag_target_ids = ()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                self._drag_mode = "subtree" if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else "node"
                self._drag_node_id = node_id
                self._drag_target_ids = self._subtree_node_ids(node_id) if self._drag_mode == "subtree" else (node_id,)
                self._selected_node_id = node_id
                self.node_selected.emit(node_id)
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                self.update()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._drag_mode in {"left_pan", "right_pan"}:
            required_button = Qt.MouseButton.LeftButton if self._drag_mode == "left_pan" else Qt.MouseButton.RightButton
            if self._press_global_pos is None or self._last_global_pos is None or not event.buttons() & required_button:
                super().mouseMoveEvent(event)
                return
            current = event.globalPosition()
            delta = current - self._last_global_pos
            total = current - self._press_global_pos
            if self._dragging or abs(total.x()) + abs(total.y()) > 3:
                self._dragging = True
                self._last_global_pos = current
                if delta.x() or delta.y():
                    self.pan_requested.emit(delta)
            event.accept()
            return

        if self._drag_mode in {"node", "subtree"}:
            if self._press_global_pos is None or self._last_global_pos is None or not event.buttons() & Qt.MouseButton.RightButton:
                super().mouseMoveEvent(event)
                return
            current = event.globalPosition()
            delta = current - self._last_global_pos
            total = current - self._press_global_pos
            if self._dragging or abs(total.x()) + abs(total.y()) > 4:
                self._dragging = True
                self._last_global_pos = current
                self._move_nodes(self._drag_target_ids, delta)
            event.accept()
            return

        if self._drag_mode in {"left_node_click", "menu_action"}:
            if self._press_global_pos is not None:
                total = event.globalPosition() - self._press_global_pos
                if abs(total.x()) + abs(total.y()) > 6:
                    self._dragging = True
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._drag_mode in {"left_pan", "left_node_click", "menu_action"}:
            mode = self._drag_mode
            was_dragging = self._dragging
            action = self._menu_press_action
            node_id = self._drag_node_id
            self.unsetCursor()
            self._press_global_pos = None
            self._last_global_pos = None
            self._dragging = False
            self._drag_mode = None
            self._drag_node_id = None
            self._drag_target_ids = ()
            self._menu_press_action = None
            if mode == "menu_action" and not was_dragging and action is not None:
                release_action = self._menu_action_at(event.position())
                if release_action == action and self._menu_node_id is not None:
                    self.menu_action_requested.emit(self._menu_node_id, action)
            elif mode == "left_node_click" and not was_dragging and node_id is not None:
                self._menu_node_id = node_id
                self.update()
            elif mode == "left_pan" and not was_dragging:
                self._menu_node_id = None
                self.update()
            event.accept()
            return

        if event.button() == Qt.MouseButton.RightButton and self._drag_mode in {"right_pan", "node", "subtree"}:
            self.unsetCursor()
            self._press_global_pos = None
            self._last_global_pos = None
            self._dragging = False
            self._drag_mode = None
            self._drag_node_id = None
            self._drag_target_ids = ()
            if getattr(self, "_layout_dirty", False):
                self._save_offsets()
                self._layout_dirty = False
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _draw_connector(self, painter: QPainter, px: float, py: float, x: float, y: float, tone: str) -> None:
        color = self._tone_color(tone)
        color.setAlpha(150)
        pen = QPen(color, max(1.2, 1.8 * self._zoom))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        dot_gap = 9 * self._zoom
        start_y = py + dot_gap if y > py else py - dot_gap
        end_y = y - dot_gap if y > py else y + dot_gap
        if abs(px - x) < 0.1:
            painter.drawLine(QPointF(px, start_y), QPointF(x, end_y))
            return
        vertical_direction = 1 if y > py else -1
        control_y = py + vertical_direction * min(max(abs(y - py) * 0.28, 18 * self._zoom), 34 * self._zoom)
        curve = QPainterPath(QPointF(px, start_y))
        curve.cubicTo(QPointF(px, control_y), QPointF(x, control_y), QPointF(x, end_y))
        painter.drawPath(curve)

    def _draw_canvas_menu(self) -> None:
        if self._menu_node_id is None:
            return
        frame, rows = self._menu_layout()
        if frame is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor(34, 211, 238, 150), max(1.0, 1.1 * self._zoom)))
        painter.setBrush(QColor(15, 23, 42, 236))
        painter.drawRoundedRect(frame, 12 * self._zoom, 12 * self._zoom)

        title_font = QFont(painter.font())
        title_font.setPointSizeF(max(7.0, 9.4 * self._zoom))
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor(226, 232, 240))
        title_rect = QRectF(frame.x() + 12 * self._zoom, frame.y() + 8 * self._zoom, frame.width() - 24 * self._zoom, 20 * self._zoom)
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, "Действия точки")

        muted_font = QFont(painter.font())
        muted_font.setPointSizeF(max(6.5, 8.0 * self._zoom))
        muted_font.setBold(False)
        painter.setFont(muted_font)
        painter.setPen(QColor(148, 163, 184))
        id_rect = QRectF(frame.x() + 12 * self._zoom, frame.y() + 28 * self._zoom, frame.width() - 24 * self._zoom, 18 * self._zoom)
        painter.drawText(id_rect, Qt.AlignLeft | Qt.AlignVCenter, self._menu_node_id)

        action_font = QFont(painter.font())
        action_font.setPointSizeF(max(6.8, 8.6 * self._zoom))
        painter.setFont(action_font)
        for _action, label, rect in rows:
            painter.setPen(QPen(QColor(51, 65, 85, 220), max(0.8, 1.0 * self._zoom)))
            painter.setBrush(QColor(30, 41, 59, 226))
            painter.drawRoundedRect(rect, 7 * self._zoom, 7 * self._zoom)
            painter.setPen(QColor(226, 232, 240))
            painter.drawText(rect.adjusted(10 * self._zoom, 0, -8 * self._zoom, 0), Qt.AlignLeft | Qt.AlignVCenter, label)

    def _menu_action_at(self, pos: QPointF) -> str | None:
        if self._menu_node_id is None:
            return None
        _frame, rows = self._menu_layout()
        for action, _label, rect in rows:
            if rect.contains(pos):
                return action
        return None

    def _menu_layout(self) -> tuple[QRectF | None, tuple[tuple[str, str, QRectF], ...]]:
        if self._menu_node_id is None:
            return None, ()
        positions = self._positions()
        if self._menu_node_id not in positions:
            return None, ()
        x, y = positions[self._menu_node_id]
        scale = self._zoom
        width = 244 * scale
        header_height = 52 * scale
        row_height = 27 * scale
        gap = 5 * scale
        actions = self._menu_actions()
        height = header_height + len(actions) * row_height + max(0, len(actions) - 1) * gap + 12 * scale
        left = x + 38 * scale
        top = y + 18 * scale
        if left + width > self.width() - 14 * scale:
            left = x - width - 38 * scale
        if top + height > self.height() - 14 * scale:
            top = y - height - 18 * scale
        left = max(14 * scale, left)
        top = max(14 * scale, top)
        frame = QRectF(left, top, width, height)
        rows: list[tuple[str, str, QRectF]] = []
        row_y = top + header_height
        for action, label in actions:
            rect = QRectF(left + 10 * scale, row_y, width - 20 * scale, row_height)
            rows.append((action, label, rect))
            row_y += row_height + gap
        return frame, tuple(rows)

    def _menu_actions(self) -> tuple[tuple[str, str], ...]:
        return (
            ("make_current", "Сделать актуальной"),
            ("mark_good", "Пометить удачной"),
            ("mark_pending", "Пометить спорной"),
            ("mark_bad", "Пометить неудачной"),
            ("continue", "Продолжить от этой точки"),
            ("center", "Центрировать на точке"),
            ("reset_node", "Сбросить смещение точки"),
            ("reset_subtree", "Сбросить смещение поддерева"),
        )

    def _node_at(self, pos: QPointF) -> str | None:
        positions = self._positions()
        candidates: list[tuple[float, str]] = []
        for node in self._nodes:
            if node.node_id not in positions:
                continue
            x, y = positions[node.node_id]
            dot_rect = QRectF(x - 18 * self._zoom, y - 18 * self._zoom, 36 * self._zoom, 36 * self._zoom)
            label_width = self._label_width(node.title)
            label_rect = QRectF(x + 20 * self._zoom, y - 17 * self._zoom, max(42.0, label_width + 22.0) * self._zoom, 34 * self._zoom)
            if dot_rect.contains(pos) or label_rect.contains(pos):
                distance = (pos.x() - x) ** 2 + (pos.y() - y) ** 2
                candidates.append((distance, node.node_id))
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[0])[1]
