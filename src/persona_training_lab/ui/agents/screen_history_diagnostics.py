from __future__ import annotations

from collections import deque
from pathlib import Path
from time import monotonic
from typing import Any

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QAction, QGuiApplication, QKeyEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.agents.screen_history_keyguard_sticky import AgentsScreen as _StickyHistoryAgentsScreen


class AgentsScreen(_StickyHistoryAgentsScreen):
    """Expose a focused trace for Ctrl/Shift/Z routing and history dispatch."""

    _DEBUG_LIMIT = 800
    _LAYOUT_FALLBACK_SECONDS = 2.0
    _LOCALE_POLL_MS = 120

    def __init__(self, view_model) -> None:
        self._history_debug_lines: deque[str] = deque(maxlen=self._DEBUG_LIMIT)
        self._history_debug_started = monotonic()
        self._history_debug_sequence = 0
        self._history_debug_dialog: QDialog | None = None
        self._history_debug_text: QPlainTextEdit | None = None
        self._layout_switch_pending_until = 0.0
        self._last_input_locale = ""
        super().__init__(view_model)

        self._install_history_debug_button()
        input_method = QGuiApplication.inputMethod()
        if input_method is not None:
            try:
                self._last_input_locale = input_method.locale().name()
            except Exception:
                self._last_input_locale = ""
            locale_changed = getattr(input_method, "localeChanged", None)
            if locale_changed is not None:
                locale_changed.connect(lambda: self._note_input_locale_change("signal"))

        self._locale_poll = QTimer(self)
        self._locale_poll.setInterval(self._LOCALE_POLL_MS)
        self._locale_poll.timeout.connect(self._poll_input_locale)
        self._locale_poll.start()
        self._debug_log("READY", screen=type(self).__name__, locale=self._last_input_locale or "—")

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if isinstance(event, QKeyEvent):
            key_name = self._history_key_name(event)
            modifiers = event.modifiers()
            relevant = key_name is not None or bool(modifiers & Qt.KeyboardModifier.ControlModifier)
            if relevant and event.type() in (
                QEvent.Type.KeyPress,
                QEvent.Type.KeyRelease,
                QEvent.Type.ShortcutOverride,
            ):
                self._debug_log(
                    "KEY_EVENT",
                    event=self._event_type_name(event.type()),
                    key_name=key_name or "other",
                    key=int(event.key()),
                    text=repr(event.text()),
                    scan=int(event.nativeScanCode()),
                    modifiers=int(modifiers),
                    repeat=event.isAutoRepeat(),
                    watched=type(watched).__name__,
                    state=self._history_state_text(),
                    queried=self._queried_modifier_text(),
                )
        elif self._KEYBOARD_LAYOUT_CHANGE is not None and event.type() == self._KEYBOARD_LAYOUT_CHANGE:
            self._debug_log("KEYBOARD_LAYOUT_CHANGE_EVENT", watched=type(watched).__name__)
            self._note_input_locale_change("event")
        return super().eventFilter(watched, event)

    def _handle_history_key_press(self, event: QKeyEvent, key_name: str) -> bool:
        if key_name == "z":
            control, _shift = self._effective_modifiers(event)
            if control and monotonic() <= self._layout_switch_pending_until:
                self._history_keys.control_down = True
                actions = self._history_keys.latch_layout_shift()
                self._layout_switch_pending_until = 0.0
                self._debug_log(
                    "LAYOUT_FALLBACK_LATCH",
                    actions=tuple(actions),
                    state=self._history_state_text(),
                )
                if actions:
                    self._dispatch_history_actions(actions)
        claimed = super()._handle_history_key_press(event, key_name)
        self._debug_log(
            "PRESS_RESULT",
            key_name=key_name,
            claimed=claimed,
            state=self._history_state_text(),
        )
        return claimed

    def _handle_history_key_release(self, key_name: str) -> bool:
        claimed = super()._handle_history_key_release(key_name)
        if key_name == "control":
            self._layout_switch_pending_until = 0.0
        self._debug_log(
            "RELEASE_RESULT",
            key_name=key_name,
            claimed=claimed,
            state=self._history_state_text(),
        )
        return claimed

    def _handle_keyboard_layout_change(self) -> None:
        self._debug_log(
            "BASE_LAYOUT_HANDLER_BEFORE",
            state=self._history_state_text(),
            queried=self._queried_modifier_text(),
        )
        super()._handle_keyboard_layout_change()
        self._debug_log("BASE_LAYOUT_HANDLER_AFTER", state=self._history_state_text())

    def _dispatch_history_actions(self, actions) -> None:
        materialized = tuple(actions)
        self._debug_log(
            "DISPATCH",
            actions=materialized,
            state=self._history_state_text(),
            sender=self._sender_text(),
        )
        super()._dispatch_history_actions(materialized)

    def _toggle_last_history_action(self) -> None:
        self._debug_log(
            "CALL_QUICK_TOGGLE",
            sender=self._sender_text(),
            state=self._history_state_text(),
            history=self._history_capabilities_text(),
        )
        super()._toggle_last_history_action()
        self._debug_log("RETURN_QUICK_TOGGLE", history=self._history_capabilities_text())

    def _undo_history_only(self) -> None:
        self._debug_log(
            "CALL_UNDO_ONLY",
            sender=self._sender_text(),
            state=self._history_state_text(),
            history=self._history_capabilities_text(),
        )
        super()._undo_history_only()
        self._debug_log("RETURN_UNDO_ONLY", history=self._history_capabilities_text())

    def _apply_history_transition(self, transition) -> None:
        self._debug_log(
            "TRANSITION",
            direction=getattr(transition, "direction", None),
            label=getattr(transition, "label", None),
            critical=getattr(transition, "critical", None),
        )
        super()._apply_history_transition(transition)

    def _reset_history_gesture(self) -> None:
        self._debug_log("RESET_GESTURE", before=self._history_state_text())
        self._layout_switch_pending_until = 0.0
        super()._reset_history_gesture()
        self._debug_log("RESET_GESTURE_DONE", after=self._history_state_text())

    def _note_input_locale_change(self, source: str) -> None:
        locale_name = self._current_input_locale()
        if locale_name:
            self._last_input_locale = locale_name
        self._layout_switch_pending_until = monotonic() + self._LAYOUT_FALLBACK_SECONDS
        self._debug_log(
            "INPUT_LOCALE_CHANGED",
            source=source,
            locale=locale_name or "—",
            pending_ms=int(self._LAYOUT_FALLBACK_SECONDS * 1000),
            state=self._history_state_text(),
            queried=self._queried_modifier_text(),
        )

    def _poll_input_locale(self) -> None:
        locale_name = self._current_input_locale()
        if not locale_name:
            return
        if not self._last_input_locale:
            self._last_input_locale = locale_name
            return
        if locale_name != self._last_input_locale:
            self._last_input_locale = locale_name
            self._note_input_locale_change("poll")

    @staticmethod
    def _current_input_locale() -> str:
        input_method = QGuiApplication.inputMethod()
        if input_method is None:
            return ""
        try:
            return input_method.locale().name()
        except Exception:
            return ""

    def _install_history_debug_button(self) -> None:
        flip_button = next(
            (
                button
                for button in self.findChildren(QPushButton)
                if button.text().replace("&", "") == "Отразить"
            ),
            None,
        )
        if flip_button is None:
            return
        layout = self._find_layout_with_widget(self.layout(), flip_button)
        if not isinstance(layout, QBoxLayout):
            return
        debug_button = QPushButton("Отладка Ctrl+Shift+Z")
        debug_button.setCursor(Qt.CursorShape.PointingHandCursor)
        debug_button.setMinimumHeight(30)
        debug_button.setProperty("secondary", True)
        debug_button.clicked.connect(self._show_history_debug)
        index = self._layout_widget_index(layout, flip_button)
        layout.insertWidget(index + 1 if index >= 0 else layout.count(), debug_button)
        self._history_debug_button = debug_button

    def _show_history_debug(self) -> None:
        if self._history_debug_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Отладка Ctrl+Shift+Z")
            dialog.resize(980, 620)
            root = QVBoxLayout(dialog)
            description = QLabel(
                "Журнал хранит только Ctrl, Shift, Z, смену раскладки и вызовы истории. "
                "Воспроизведите проблему, затем нажмите «Копировать»."
            )
            description.setWordWrap(True)
            root.addWidget(description)
            text = QPlainTextEdit()
            text.setReadOnly(True)
            root.addWidget(text, 1)
            buttons = QHBoxLayout()
            copy_button = QPushButton("Копировать")
            save_button = QPushButton("Сохранить лог")
            clear_button = QPushButton("Очистить")
            close_button = QPushButton("Закрыть")
            copy_button.clicked.connect(self._copy_history_debug)
            save_button.clicked.connect(self._save_history_debug)
            clear_button.clicked.connect(self._clear_history_debug)
            close_button.clicked.connect(dialog.close)
            buttons.addWidget(copy_button)
            buttons.addWidget(save_button)
            buttons.addWidget(clear_button)
            buttons.addStretch(1)
            buttons.addWidget(close_button)
            root.addLayout(buttons)
            self._history_debug_dialog = dialog
            self._history_debug_text = text
        self._refresh_history_debug_text()
        self._history_debug_dialog.show()
        self._history_debug_dialog.raise_()
        self._history_debug_dialog.activateWindow()

    def _copy_history_debug(self) -> None:
        QApplication.clipboard().setText(self._history_debug_dump())

    def _save_history_debug(self) -> None:
        path = Path.home() / ".persona_training_lab" / "history_input_debug.log"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._history_debug_dump(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "Не удалось сохранить лог", str(exc))
            return
        QMessageBox.information(self, "Лог сохранён", str(path))

    def _clear_history_debug(self) -> None:
        self._history_debug_lines.clear()
        self._history_debug_started = monotonic()
        self._history_debug_sequence = 0
        self._debug_log("LOG_CLEARED")

    def _refresh_history_debug_text(self) -> None:
        if self._history_debug_text is None:
            return
        scrollbar = self._history_debug_text.verticalScrollBar()
        at_end = scrollbar.value() >= scrollbar.maximum() - 3
        self._history_debug_text.setPlainText(self._history_debug_dump())
        if at_end:
            scrollbar.setValue(scrollbar.maximum())

    def _history_debug_dump(self) -> str:
        return "\n".join(self._history_debug_lines)

    def _debug_log(self, category: str, **fields: Any) -> None:
        self._history_debug_sequence += 1
        elapsed_ms = int((monotonic() - self._history_debug_started) * 1000)
        parts = [f"{self._history_debug_sequence:04d}", f"+{elapsed_ms:06d}ms", category]
        for key, value in fields.items():
            parts.append(f"{key}={value}")
        self._history_debug_lines.append(" | ".join(parts))
        if self._history_debug_dialog is not None and self._history_debug_dialog.isVisible():
            QTimer.singleShot(0, self._refresh_history_debug_text)

    def _history_state_text(self) -> str:
        state = getattr(self, "_history_keys", None)
        if state is None:
            return "uninitialised"
        return (
            f"ctrl={state.control_down},shift={state.shift_down},"
            f"shift_latched={state.shift_latched},layout_latched={state.layout_shift_latched},"
            f"z={state.z_down},mode={state.mode},strict={state.strict_undo_requested}"
        )

    def _queried_modifier_text(self) -> str:
        try:
            control, shift = self._queried_modifiers()
        except Exception as exc:
            return f"error:{type(exc).__name__}"
        return f"ctrl={control},shift={shift}"

    def _history_capabilities_text(self) -> str:
        state_store = getattr(self, "_state", None)
        if state_store is None:
            return "unavailable"
        try:
            return (
                f"undo={state_store.can_undo()},redo={state_store.can_redo()},"
                f"toggle={state_store.history_toggle_text()}"
            )
        except Exception as exc:
            return f"error:{type(exc).__name__}"

    def _sender_text(self) -> str:
        sender = self.sender()
        if sender is None:
            return "direct"
        if isinstance(sender, QShortcut):
            return (
                f"QShortcut(key={sender.key().toString(QKeySequence.SequenceFormat.PortableText)!r},"
                f"enabled={sender.isEnabled()})"
            )
        if isinstance(sender, QAction):
            shortcuts = [item.toString(QKeySequence.SequenceFormat.PortableText) for item in sender.shortcuts()]
            return f"QAction(text={sender.text()!r},shortcuts={shortcuts})"
        if isinstance(sender, QTimer):
            return f"QTimer(interval={sender.interval()},active={sender.isActive()})"
        return f"{type(sender).__name__}(name={getattr(sender, 'objectName', lambda: '')()!r})"

    @staticmethod
    def _event_type_name(event_type: QEvent.Type) -> str:
        try:
            return event_type.name
        except AttributeError:
            return str(int(event_type))

    @classmethod
    def _find_layout_with_widget(cls, layout: QLayout | None, target: QWidget) -> QLayout | None:
        if layout is None:
            return None
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item.widget() is target:
                return layout
            child = item.layout()
            found = cls._find_layout_with_widget(child, target)
            if found is not None:
                return found
        return None

    @staticmethod
    def _layout_widget_index(layout: QLayout, target: QWidget) -> int:
        for index in range(layout.count()):
            if layout.itemAt(index).widget() is target:
                return index
        return -1
