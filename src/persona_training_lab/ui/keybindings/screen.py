from __future__ import annotations

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QKeySequenceEdit,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import (
    render_user_message,
    text as localized_text,
)
from persona_training_lab.ui.keybindings.definitions import (
    MOUSE_BUTTON_IDS,
    MOUSE_MODIFIER_IDS,
)
from persona_training_lab.ui.keybindings.draft_session import (
    DraftChangeResult,
    KeyBindingDraftSession,
)
from persona_training_lab.ui.keybindings.manager import KeyBindingManager
from persona_training_lab.ui.themes.manager import _resolve


I18N_KEY_PREFIXES = (
    "keybindings.binding.",
    "keybindings.mouse_binding.",
    "keybindings.mouse.button.",
    "keybindings.mouse.modifier.",
)

_MODIFIER_KEYS = {
    Qt.Key.Key_Shift,
    Qt.Key.Key_Control,
    Qt.Key.Key_Alt,
    Qt.Key.Key_Meta,
}

_MOUSE_BUTTON_NAMES = {
    Qt.MouseButton.LeftButton: "left",
    Qt.MouseButton.RightButton: "right",
    Qt.MouseButton.MiddleButton: "middle",
    Qt.MouseButton.BackButton: "back",
    Qt.MouseButton.ForwardButton: "forward",
}


class _BindingValueChip(QPushButton):
    def __init__(self, *, minimum_width: int) -> None:
        super().__init__("—")
        self.setMinimumWidth(minimum_width)
        self.setMinimumHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._capturing = False
        self._pulse_on = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(430)
        self._pulse_timer.timeout.connect(self._toggle_pulse)

    def set_capturing(self, active: bool) -> None:
        if self._capturing == active:
            return
        self._capturing = active
        self._pulse_on = active
        if active:
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
        self.update()

    def _toggle_pulse(self) -> None:
        self._pulse_on = not self._pulse_on
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        app = QApplication.instance()
        theme_name = app.property("ptl_theme_name") if app is not None else None
        accent_name = app.property("ptl_accent_name") if app is not None else None
        theme, accent = _resolve(theme_name, accent_name)

        if self._capturing:
            background = (
                accent["accent_soft"]
                if self._pulse_on
                else theme["surface_alt"]
            )
            border = accent["accent"]
            text = theme["text_primary"]
        elif self.isDown():
            background = accent["accent_pressed"]
            border = accent["accent_pressed"]
            text = "#ffffff"
        elif self.underMouse():
            background = theme["selection_bg"]
            border = accent["accent"]
            text = theme["text_primary"]
        else:
            background = theme["surface_alt"]
            border = theme["border_soft"]
            text = theme["text_secondary"]

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = min(15.0, rect.height() / 2.0)
        painter.setPen(QPen(QColor(border), 1.2))
        painter.setBrush(QColor(background))
        painter.drawRoundedRect(rect, radius, radius)
        painter.setPen(QColor(text))
        font = self.font()
        font.setBold(True)
        font.setPointSizeF(max(8.0, font.pointSizeF() - 1.0))
        painter.setFont(font)
        painter.drawText(
            rect.adjusted(10, 0, -10, 0),
            Qt.AlignmentFlag.AlignCenter,
            self.text(),
        )


class _ConflictPanelCard(PanelCard):
    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__(title, subtitle)
        self._has_conflict = False

    def set_conflict(self, active: bool) -> None:
        if self._has_conflict == active:
            return
        self._has_conflict = active
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)
        if not self._has_conflict:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#ef4444"), 2.0))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 21, 21)


class _ShortcutCaptureDialog(QDialog):
    def __init__(
        self,
        title_key: str,
        current_sequence: str,
        localization: LocalizationManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title_key = title_key
        self._localization = localization
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        self._heading = QLabel()
        self._heading.setObjectName("CardTitle")
        root.addWidget(self._heading)
        self._note = make_muted_label("")
        root.addWidget(self._note)

        current = QKeySequence.fromString(
            current_sequence,
            QKeySequence.SequenceFormat.PortableText,
        )
        self._editor = QKeySequenceEdit(current)
        if hasattr(self._editor, "setMaximumSequenceLength"):
            self._editor.setMaximumSequenceLength(1)
        if hasattr(self._editor, "setClearButtonEnabled"):
            self._editor.setClearButtonEnabled(True)
        root.addWidget(self._editor)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._save = self._buttons.button(QDialogButtonBox.StandardButton.Save)
        self._cancel = self._buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

        self._apply_language()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        self.setWindowTitle(self._text("keybindings.dialog.shortcut.title"))
        self._heading.setText(self._text(self._title_key))
        self._note.setText(self._text("keybindings.dialog.shortcut.note"))
        if self._save is not None:
            self._save.setText(self._text("keybindings.action.save"))
        if self._cancel is not None:
            self._cancel.setText(self._text("keybindings.action.cancel"))

    def sequence(self) -> str:
        return self._editor.keySequence().toString(
            QKeySequence.SequenceFormat.PortableText
        )


class _MouseGestureDialog(QDialog):
    def __init__(
        self,
        title_key: str,
        current_button: str,
        current_modifier: str,
        *,
        wheel_only: bool,
        localization: LocalizationManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title_key = title_key
        self._localization = localization
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        self._heading = QLabel()
        self._heading.setObjectName("CardTitle")
        root.addWidget(self._heading)
        self._note = make_muted_label("")
        root.addWidget(self._note)

        self._button_label = QLabel()
        root.addWidget(self._button_label)
        self._button_box = QComboBox()
        button_ids = (
            ("wheel",)
            if wheel_only
            else tuple(key for key in MOUSE_BUTTON_IDS if key != "wheel")
        )
        for key in button_ids:
            self._button_box.addItem("", key)
        self._button_box.setCurrentIndex(
            max(0, self._button_box.findData(current_button))
        )
        self._button_box.setEnabled(not wheel_only)
        root.addWidget(self._button_box)

        self._modifier_label = QLabel()
        root.addWidget(self._modifier_label)
        self._modifier_box = QComboBox()
        for key in MOUSE_MODIFIER_IDS:
            self._modifier_box.addItem("", key)
        self._modifier_box.setCurrentIndex(
            max(0, self._modifier_box.findData(current_modifier))
        )
        root.addWidget(self._modifier_box)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._save = self._buttons.button(QDialogButtonBox.StandardButton.Save)
        self._cancel = self._buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

        self._apply_language()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        self.setWindowTitle(self._text("keybindings.dialog.mouse.title"))
        self._heading.setText(self._text(self._title_key))
        self._note.setText(self._text("keybindings.dialog.mouse.note"))
        self._button_label.setText(self._text("keybindings.dialog.mouse.button"))
        self._modifier_label.setText(
            self._text("keybindings.dialog.mouse.modifier")
        )
        current_button = self._button_box.currentData()
        for index in range(self._button_box.count()):
            key = str(self._button_box.itemData(index))
            self._button_box.setItemText(
                index,
                self._text(f"keybindings.mouse.button.{key}"),
            )
        self._button_box.setCurrentIndex(
            max(0, self._button_box.findData(current_button))
        )
        current_modifier = self._modifier_box.currentData()
        for index in range(self._modifier_box.count()):
            key = str(self._modifier_box.itemData(index))
            self._modifier_box.setItemText(
                index,
                self._text(f"keybindings.mouse.modifier.{key}"),
            )
        self._modifier_box.setCurrentIndex(
            max(0, self._modifier_box.findData(current_modifier))
        )
        if self._save is not None:
            self._save.setText(self._text("keybindings.action.save"))
        if self._cancel is not None:
            self._cancel.setText(self._text("keybindings.action.cancel"))

    def button_name(self) -> str:
        return str(self._button_box.currentData())

    def modifier_name(self) -> str:
        return str(self._modifier_box.currentData())


class KeyBindingsScreen(QWidget):
    def __init__(
        self,
        manager: KeyBindingManager,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._manager = manager
        self._localization = localization
        self._draft = KeyBindingDraftSession(manager)
        self._sequence_chips: dict[str, _BindingValueChip] = {}
        self._mouse_chips: dict[str, _BindingValueChip] = {}
        self._keyboard_cards: dict[str, _ConflictPanelCard] = {}
        self._mouse_cards: dict[str, _ConflictPanelCard] = {}
        self._keyboard_conflict_labels: dict[str, QLabel] = {}
        self._mouse_conflict_labels: dict[str, QLabel] = {}
        self._keyboard_edit_buttons: dict[str, QPushButton] = {}
        self._keyboard_reset_buttons: dict[str, QPushButton] = {}
        self._mouse_edit_buttons: dict[str, QPushButton] = {}
        self._mouse_reset_buttons: dict[str, QPushButton] = {}
        self._capture_kind: str | None = None
        self._capture_binding_id: str | None = None
        self._capture_filter_installed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        self._header = PanelCard("", "")
        header_actions = QWidget()
        header_actions.setProperty("transparentBg", True)
        header_actions_layout = QHBoxLayout(header_actions)
        header_actions_layout.setContentsMargins(0, 0, 0, 0)
        header_actions_layout.setSpacing(10)
        path_label = make_muted_label(str(self._manager.storage_path))
        path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._reset_all_button = QPushButton()
        self._reset_all_button.setObjectName("SecondaryButton")
        self._reset_all_button.clicked.connect(self._reset_all)
        header_actions_layout.addWidget(path_label, 1)
        header_actions_layout.addWidget(self._reset_all_button, 0)
        self._header.add_widget(header_actions)
        self._warning_label: QLabel | None = None
        if self._manager.last_error_message is not None:
            self._warning_label = QLabel()
            self._warning_label.setObjectName("MutedText")
            self._warning_label.setWordWrap(True)
            self._header.add_widget(self._warning_label)
        root.addWidget(self._header)

        scroll = QScrollArea()
        scroll.setObjectName("StableScrollArea")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored
        )
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        content = QWidget()
        content.setProperty("transparentBg", True)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self._bindings_title = QLabel()
        self._bindings_title.setObjectName("SectionTitle")
        content_layout.addWidget(self._bindings_title)
        for definition in self._manager.definitions():
            content_layout.addWidget(self._binding_card(definition.binding_id))

        self._mouse_title = QLabel()
        self._mouse_title.setObjectName("SectionTitle")
        content_layout.addWidget(self._mouse_title)
        for definition in self._manager.mouse_definitions():
            content_layout.addWidget(
                self._mouse_binding_card(definition.binding_id)
            )

        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self._manager.bindings_changed.connect(self._on_manager_changed)
        self._apply_language()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        self._header.set_title(self._text("keybindings.header.title"))
        self._header.set_subtitle(self._text("keybindings.header.subtitle"))
        self._reset_all_button.setText(
            self._text("keybindings.header.reset_all")
        )
        self._bindings_title.setText(self._text("keybindings.section.keyboard"))
        self._mouse_title.setText(self._text("keybindings.section.mouse"))
        if (
            self._warning_label is not None
            and self._manager.last_error_message is not None
        ):
            self._warning_label.setText(
                render_user_message(
                    self._localization,
                    self._manager.last_error_message,
                )
            )

        for definition in self._manager.definitions():
            binding_id = definition.binding_id
            card = self._keyboard_cards[binding_id]
            card.set_title(self._text(definition.title_key))
            card.set_subtitle(self._text(definition.description_key))
            self._keyboard_edit_buttons[binding_id].setText(
                self._text("keybindings.action.edit")
            )
            self._keyboard_reset_buttons[binding_id].setText(
                self._text("keybindings.action.default")
            )
            self._sequence_chips[binding_id].setToolTip(
                self._text("keybindings.chip.tooltip")
            )

        for definition in self._manager.mouse_definitions():
            binding_id = definition.binding_id
            card = self._mouse_cards[binding_id]
            card.set_title(self._text(definition.title_key))
            card.set_subtitle(self._text(definition.description_key))
            self._mouse_edit_buttons[binding_id].setText(
                self._text("keybindings.action.edit")
            )
            self._mouse_reset_buttons[binding_id].setText(
                self._text("keybindings.action.default")
            )
            self._mouse_chips[binding_id].setToolTip(
                self._text("keybindings.chip.tooltip")
            )

        self._refresh_bindings()

    def _binding_card(self, binding_id: str) -> QWidget:
        card = _ConflictPanelCard("", "")
        self._keyboard_cards[binding_id] = card

        row = QWidget()
        row.setProperty("transparentBg", True)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        sequence = _BindingValueChip(minimum_width=150)
        sequence.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._schedule_capture(
                "keyboard", item_id
            )
        )
        self._sequence_chips[binding_id] = sequence

        edit = QPushButton()
        edit.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._edit_binding(
                item_id
            )
        )
        self._keyboard_edit_buttons[binding_id] = edit
        reset = QPushButton()
        reset.setObjectName("SecondaryButton")
        reset.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._reset_binding(
                item_id
            )
        )
        self._keyboard_reset_buttons[binding_id] = reset

        layout.addWidget(sequence, 0)
        layout.addStretch(1)
        layout.addWidget(edit, 0)
        layout.addWidget(reset, 0)
        card.add_widget(row)

        conflict = QLabel()
        conflict.setWordWrap(True)
        conflict.setStyleSheet("color: #ef4444; font-weight: 700;")
        conflict.hide()
        self._keyboard_conflict_labels[binding_id] = conflict
        card.add_widget(conflict)
        return card

    def _mouse_binding_card(self, binding_id: str) -> QWidget:
        card = _ConflictPanelCard("", "")
        self._mouse_cards[binding_id] = card

        row = QWidget()
        row.setProperty("transparentBg", True)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        gesture = _BindingValueChip(minimum_width=210)
        gesture.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._schedule_capture(
                "mouse", item_id
            )
        )
        self._mouse_chips[binding_id] = gesture

        edit = QPushButton()
        edit.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._edit_mouse_binding(
                item_id
            )
        )
        self._mouse_edit_buttons[binding_id] = edit
        reset = QPushButton()
        reset.setObjectName("SecondaryButton")
        reset.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._reset_mouse_binding(
                item_id
            )
        )
        self._mouse_reset_buttons[binding_id] = reset

        layout.addWidget(gesture, 0)
        layout.addStretch(1)
        layout.addWidget(edit, 0)
        layout.addWidget(reset, 0)
        card.add_widget(row)

        conflict = QLabel()
        conflict.setWordWrap(True)
        conflict.setStyleSheet("color: #ef4444; font-weight: 700;")
        conflict.hide()
        self._mouse_conflict_labels[binding_id] = conflict
        card.add_widget(conflict)
        return card

    def _schedule_capture(self, kind: str, binding_id: str) -> None:
        if self._capture_kind == kind and self._capture_binding_id == binding_id:
            self._cancel_capture()
            return
        self._cancel_capture()
        QTimer.singleShot(0, lambda: self._start_capture(kind, binding_id))

    def _start_capture(self, kind: str, binding_id: str) -> None:
        self._capture_kind = kind
        self._capture_binding_id = binding_id
        chips = (
            self._sequence_chips if kind == "keyboard" else self._mouse_chips
        )
        chips[binding_id].set_capturing(True)
        app = QApplication.instance()
        if app is not None and not self._capture_filter_installed:
            app.installEventFilter(self)
            self._capture_filter_installed = True

    def _cancel_capture(self) -> None:
        if self._capture_kind == "keyboard" and self._capture_binding_id:
            self._sequence_chips[self._capture_binding_id].set_capturing(False)
        elif self._capture_kind == "mouse" and self._capture_binding_id:
            self._mouse_chips[self._capture_binding_id].set_capturing(False)
        self._capture_kind = None
        self._capture_binding_id = None
        app = QApplication.instance()
        if app is not None and self._capture_filter_installed:
            app.removeEventFilter(self)
        self._capture_filter_installed = False

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if self._capture_kind is None or self._capture_binding_id is None:
            return super().eventFilter(watched, event)

        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self._cancel_capture()
                return True
            if self._capture_kind == "keyboard":
                if event.key() in _MODIFIER_KEYS:
                    return True
                sequence = QKeySequence(event.keyCombination()).toString(
                    QKeySequence.SequenceFormat.PortableText
                )
                binding_id = self._capture_binding_id
                self._cancel_capture()
                self._handle_result(
                    self._draft.set_sequence(binding_id, sequence)
                )
                self._refresh_bindings()
                return True
            return event.key() in _MODIFIER_KEYS

        if self._capture_kind == "mouse":
            if event.type() == QEvent.Type.MouseButtonPress:
                button = _MOUSE_BUTTON_NAMES.get(event.button())
                if button is None:
                    return True
                modifier = self._modifier_name(event.modifiers())
                binding_id = self._capture_binding_id
                self._cancel_capture()
                if modifier is None:
                    self._show_message(
                        "keybindings.dialog.change_failed.title",
                        UserMessage("keybindings.error.too_many_modifiers"),
                        QMessageBox.Icon.Warning,
                    )
                else:
                    self._handle_result(
                        self._draft.set_mouse_binding(
                            binding_id,
                            button,
                            modifier,
                        )
                    )
                self._refresh_bindings()
                return True
            if event.type() == QEvent.Type.Wheel:
                modifier = self._modifier_name(event.modifiers())
                binding_id = self._capture_binding_id
                self._cancel_capture()
                if modifier is None:
                    self._show_message(
                        "keybindings.dialog.change_failed.title",
                        UserMessage("keybindings.error.too_many_modifiers"),
                        QMessageBox.Icon.Warning,
                    )
                else:
                    self._handle_result(
                        self._draft.set_mouse_binding(
                            binding_id,
                            "wheel",
                            modifier,
                        )
                    )
                self._refresh_bindings()
                return True

        return super().eventFilter(watched, event)

    @staticmethod
    def _modifier_name(modifiers: Qt.KeyboardModifier) -> str | None:
        known = (
            (Qt.KeyboardModifier.ShiftModifier, "shift"),
            (Qt.KeyboardModifier.ControlModifier, "control"),
            (Qt.KeyboardModifier.AltModifier, "alt"),
            (Qt.KeyboardModifier.MetaModifier, "meta"),
        )
        active = [name for flag, name in known if modifiers & flag]
        if len(active) > 1:
            return None
        return active[0] if active else "none"

    def _edit_binding(self, binding_id: str) -> None:
        self._cancel_capture()
        definition = self._manager.definition(binding_id)
        dialog = _ShortcutCaptureDialog(
            definition.title_key,
            self._draft.sequence(binding_id),
            self._localization,
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._handle_result(
            self._draft.set_sequence(binding_id, dialog.sequence())
        )
        self._refresh_bindings()

    def _edit_mouse_binding(self, binding_id: str) -> None:
        self._cancel_capture()
        definition = self._manager.mouse_definition(binding_id)
        current = self._draft.mouse_binding(binding_id)
        dialog = _MouseGestureDialog(
            definition.title_key,
            current.button,
            current.modifier,
            wheel_only=definition.trigger == "wheel",
            localization=self._localization,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._handle_result(
            self._draft.set_mouse_binding(
                binding_id,
                dialog.button_name(),
                dialog.modifier_name(),
            )
        )
        self._refresh_bindings()

    def _reset_binding(self, binding_id: str) -> None:
        self._cancel_capture()
        self._handle_result(self._draft.reset_binding(binding_id))
        self._refresh_bindings()

    def _reset_mouse_binding(self, binding_id: str) -> None:
        self._cancel_capture()
        self._handle_result(self._draft.reset_mouse_binding(binding_id))
        self._refresh_bindings()

    def _reset_all(self) -> None:
        self._cancel_capture()
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle(self._text("keybindings.dialog.reset.title"))
        dialog.setText(self._text("keybindings.dialog.reset.text"))
        dialog.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        yes = dialog.button(QMessageBox.StandardButton.Yes)
        no = dialog.button(QMessageBox.StandardButton.No)
        if yes is not None:
            yes.setText(self._text("keybindings.action.restore"))
        if no is not None:
            no.setText(self._text("keybindings.action.cancel"))
        dialog.exec()
        if yes is None or dialog.clickedButton() is not yes:
            return
        self._handle_result(self._draft.reset_all())
        self._refresh_bindings()

    def request_leave_workspace(self) -> bool:
        self._cancel_capture()
        if not self._draft.has_conflicts:
            return True

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle(self._text("keybindings.dialog.conflicts.title"))
        dialog.setText(self._text("keybindings.dialog.conflicts.text"))
        fix = dialog.addButton(
            self._text("keybindings.action.fix_conflicts"),
            QMessageBox.ButtonRole.RejectRole,
        )
        discard = dialog.addButton(
            self._text("keybindings.action.discard_conflicts"),
            QMessageBox.ButtonRole.DestructiveRole,
        )
        dialog.setDefaultButton(fix)
        dialog.exec()
        if dialog.clickedButton() is not discard:
            return False

        result = self._draft.discard_conflicting_changes()
        self._handle_result(result)
        self._refresh_bindings()
        return result.accepted and not self._draft.has_conflicts

    def _handle_result(self, result: DraftChangeResult) -> None:
        if result.accepted or result.message is None:
            return
        self._show_message(
            "keybindings.dialog.change_failed.title",
            result.message,
            QMessageBox.Icon.Warning,
        )

    def _show_message(
        self,
        title_key: str,
        message: UserMessage,
        icon: QMessageBox.Icon,
    ) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(icon)
        dialog.setWindowTitle(self._text(title_key))
        dialog.setText(render_user_message(self._localization, message))
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        ok = dialog.button(QMessageBox.StandardButton.Ok)
        if ok is not None:
            ok.setText(self._text("keybindings.action.understood"))
        dialog.exec()

    def _on_manager_changed(self) -> None:
        self._draft.rebase_if_clean()
        self._refresh_bindings()

    def _mouse_binding_text(self, binding_id: str) -> str:
        binding = self._draft.mouse_binding(binding_id)
        button = self._text(f"keybindings.mouse.button.{binding.button}")
        modifier = self._text(
            f"keybindings.mouse.modifier.{binding.modifier}"
        )
        if binding.modifier == "none":
            return button
        return f"{modifier} + {button}"

    def _conflict_text(self, binding_id: str, *, mouse: bool) -> str:
        conflicts = (
            self._draft.mouse_conflicts()
            if mouse
            else self._draft.keyboard_conflicts()
        )
        partner_ids = conflicts.get(binding_id, ())
        if not partner_ids:
            return ""
        if mouse:
            title_keys = [
                self._manager.mouse_definition(item).title_key
                for item in partner_ids
            ]
        else:
            title_keys = [
                self._manager.definition(item).title_key
                for item in partner_ids
            ]
        titles = ", ".join(
            f"«{self._text(title_key)}»" for title_key in title_keys
        )
        return self._text("keybindings.conflict.with", titles=titles)

    def _refresh_bindings(self) -> None:
        keyboard_conflicts = self._draft.keyboard_conflicts()
        mouse_conflicts = self._draft.mouse_conflicts()

        for binding_id, chip in self._sequence_chips.items():
            chip.setText(
                self._draft.sequence(binding_id)
                or self._text("keybindings.chip.unassigned")
            )
            has_conflict = binding_id in keyboard_conflicts
            card = self._keyboard_cards[binding_id]
            label = self._keyboard_conflict_labels[binding_id]
            card.set_conflict(has_conflict)
            label.setText(self._conflict_text(binding_id, mouse=False))
            label.setVisible(has_conflict)

        for binding_id, chip in self._mouse_chips.items():
            chip.setText(self._mouse_binding_text(binding_id))
            has_conflict = binding_id in mouse_conflicts
            card = self._mouse_cards[binding_id]
            label = self._mouse_conflict_labels[binding_id]
            card.set_conflict(has_conflict)
            label.setText(self._conflict_text(binding_id, mouse=True))
            label.setVisible(has_conflict)

    def _refresh_sequences(self) -> None:
        # Compatibility for older tests and callers.
        self._refresh_bindings()
