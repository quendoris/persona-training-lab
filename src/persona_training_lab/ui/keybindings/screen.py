from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractScrollArea,
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

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.keybindings.definitions import (
    MOUSE_BUTTON_LABELS,
    MOUSE_MODIFIER_LABELS,
)
from persona_training_lab.ui.keybindings.manager import (
    BindingChangeResult,
    KeyBindingManager,
    MouseBindingChangeResult,
)


class _ShortcutCaptureDialog(QDialog):
    def __init__(
        self,
        title: str,
        current_sequence: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Изменить сочетание")
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        heading = QLabel(title)
        heading.setObjectName("CardTitle")
        root.addWidget(heading)
        root.addWidget(
            make_muted_label(
                "Нажмите новое сочетание. Оно будет применено сразу после сохранения."
            )
        )

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
        root.addWidget(self._dialog_buttons())

    def _dialog_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if save is not None:
            save.setText("Сохранить")
        if cancel is not None:
            cancel.setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        return buttons

    def sequence(self) -> str:
        return self._editor.keySequence().toString(
            QKeySequence.SequenceFormat.PortableText
        )


class _MouseGestureDialog(QDialog):
    def __init__(
        self,
        title: str,
        current_button: str,
        current_modifier: str,
        *,
        wheel_only: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Изменить жест мыши")
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        heading = QLabel(title)
        heading.setObjectName("CardTitle")
        root.addWidget(heading)
        root.addWidget(
            make_muted_label(
                "Выберите кнопку и модификатор. Изменение применяется сразу после сохранения."
            )
        )

        root.addWidget(QLabel("Кнопка мыши"))
        self._button_box = QComboBox()
        button_items = (
            (("wheel", MOUSE_BUTTON_LABELS["wheel"]),)
            if wheel_only
            else tuple(
                (key, label)
                for key, label in MOUSE_BUTTON_LABELS.items()
                if key != "wheel"
            )
        )
        for key, label in button_items:
            self._button_box.addItem(label, key)
        self._button_box.setCurrentIndex(
            max(0, self._button_box.findData(current_button))
        )
        self._button_box.setEnabled(not wheel_only)
        root.addWidget(self._button_box)

        root.addWidget(QLabel("Модификатор"))
        self._modifier_box = QComboBox()
        for key, label in MOUSE_MODIFIER_LABELS.items():
            self._modifier_box.addItem(label, key)
        self._modifier_box.setCurrentIndex(
            max(0, self._modifier_box.findData(current_modifier))
        )
        root.addWidget(self._modifier_box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save = buttons.button(QDialogButtonBox.StandardButton.Save)
        cancel = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if save is not None:
            save.setText("Сохранить")
        if cancel is not None:
            cancel.setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def button_name(self) -> str:
        return str(self._button_box.currentData())

    def modifier_name(self) -> str:
        return str(self._modifier_box.currentData())


class KeyBindingsScreen(QWidget):
    def __init__(self, manager: KeyBindingManager) -> None:
        super().__init__()
        self._manager = manager
        self._sequence_labels: dict[str, QLabel] = {}
        self._mouse_labels: dict[str, QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        header = PanelCard(
            "Назначения клавиш и мыши",
            "Клавиши и жесты canvas применяются сразу, проверяются на конфликты и сохраняются между запусками.",
        )
        header_actions = QWidget()
        header_actions.setProperty("transparentBg", True)
        header_actions_layout = QHBoxLayout(header_actions)
        header_actions_layout.setContentsMargins(0, 0, 0, 0)
        header_actions_layout.setSpacing(10)
        path_label = make_muted_label(str(self._manager.storage_path))
        path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        reset_all = QPushButton("Вернуть все значения по умолчанию")
        reset_all.setObjectName("SecondaryButton")
        reset_all.clicked.connect(self._reset_all)
        header_actions_layout.addWidget(path_label, 1)
        header_actions_layout.addWidget(reset_all, 0)
        header.add_widget(header_actions)
        if self._manager.last_error:
            warning = QLabel(self._manager.last_error)
            warning.setObjectName("MutedText")
            warning.setWordWrap(True)
            header.add_widget(warning)
        root.addWidget(header)

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

        bindings_title = QLabel("Клавиатура")
        bindings_title.setObjectName("SectionTitle")
        content_layout.addWidget(bindings_title)
        for definition in self._manager.definitions():
            content_layout.addWidget(
                self._binding_card(definition.binding_id)
            )

        mouse_title = QLabel("Мышь и canvas")
        mouse_title.setObjectName("SectionTitle")
        content_layout.addWidget(mouse_title)
        for definition in self._manager.mouse_definitions():
            content_layout.addWidget(
                self._mouse_binding_card(definition.binding_id)
            )

        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self._manager.bindings_changed.connect(self._refresh_bindings)
        self._refresh_bindings()

    def _binding_card(self, binding_id: str) -> QWidget:
        definition = self._manager.definition(binding_id)
        card = PanelCard(definition.title, definition.description)

        row = QWidget()
        row.setProperty("transparentBg", True)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        sequence = QLabel("—")
        sequence.setObjectName("TelemetryChip")
        sequence.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sequence.setMinimumWidth(150)
        self._sequence_labels[binding_id] = sequence

        edit = QPushButton("Изменить")
        edit.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._edit_binding(
                item_id
            )
        )
        reset = QPushButton("По умолчанию")
        reset.setObjectName("SecondaryButton")
        reset.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._reset_binding(
                item_id
            )
        )

        layout.addWidget(sequence, 0)
        layout.addStretch(1)
        layout.addWidget(edit, 0)
        layout.addWidget(reset, 0)
        card.add_widget(row)
        return card

    def _mouse_binding_card(self, binding_id: str) -> QWidget:
        definition = self._manager.mouse_definition(binding_id)
        card = PanelCard(definition.title, definition.description)

        row = QWidget()
        row.setProperty("transparentBg", True)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        gesture = QLabel("—")
        gesture.setObjectName("TelemetryChip")
        gesture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gesture.setMinimumWidth(210)
        gesture.setWordWrap(True)
        self._mouse_labels[binding_id] = gesture

        edit = QPushButton("Изменить")
        edit.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._edit_mouse_binding(
                item_id
            )
        )
        reset = QPushButton("По умолчанию")
        reset.setObjectName("SecondaryButton")
        reset.clicked.connect(
            lambda _checked=False, item_id=binding_id: self._reset_mouse_binding(
                item_id
            )
        )

        layout.addWidget(gesture, 0)
        layout.addStretch(1)
        layout.addWidget(edit, 0)
        layout.addWidget(reset, 0)
        card.add_widget(row)
        return card

    def _edit_binding(self, binding_id: str) -> None:
        definition = self._manager.definition(binding_id)
        dialog = _ShortcutCaptureDialog(
            definition.title,
            self._manager.sequence(binding_id),
            self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._handle_result(
            self._manager.set_sequence(binding_id, dialog.sequence())
        )

    def _edit_mouse_binding(self, binding_id: str) -> None:
        definition = self._manager.mouse_definition(binding_id)
        current = self._manager.mouse_binding(binding_id)
        dialog = _MouseGestureDialog(
            definition.title,
            current.button,
            current.modifier,
            wheel_only=definition.trigger == "wheel",
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._handle_result(
            self._manager.set_mouse_binding(
                binding_id,
                dialog.button_name(),
                dialog.modifier_name(),
            )
        )

    def _reset_binding(self, binding_id: str) -> None:
        self._handle_result(self._manager.reset_binding(binding_id))

    def _reset_mouse_binding(self, binding_id: str) -> None:
        self._handle_result(self._manager.reset_mouse_binding(binding_id))

    def _reset_all(self) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle("Вернуть стандартные назначения?")
        dialog.setText(
            "Все изменённые клавиши и жесты мыши будут заменены значениями по умолчанию."
        )
        dialog.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        dialog.setDefaultButton(QMessageBox.StandardButton.No)
        yes = dialog.button(QMessageBox.StandardButton.Yes)
        no = dialog.button(QMessageBox.StandardButton.No)
        if yes is not None:
            yes.setText("Вернуть")
        if no is not None:
            no.setText("Отмена")
        dialog.exec()
        if yes is None or dialog.clickedButton() is not yes:
            return
        self._handle_result(self._manager.reset_all())

    def _handle_result(
        self,
        result: BindingChangeResult | MouseBindingChangeResult,
    ) -> None:
        if result.accepted:
            return
        if result.conflict_title:
            self._show_message(
                "Конфликт назначений",
                f"Этот жест уже назначен действию «{result.conflict_title}». Выберите другой.",
                QMessageBox.Icon.Warning,
            )
            return
        self._show_message(
            "Не удалось изменить назначение",
            result.error,
            QMessageBox.Icon.Warning,
        )

    def _show_message(
        self,
        title: str,
        text: str,
        icon: QMessageBox.Icon,
    ) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(icon)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        ok = dialog.button(QMessageBox.StandardButton.Ok)
        if ok is not None:
            ok.setText("Понятно")
        dialog.exec()

    def _refresh_bindings(self) -> None:
        for binding_id, label in self._sequence_labels.items():
            label.setText(
                self._manager.sequence(binding_id) or "Не назначено"
            )
        for binding_id, label in self._mouse_labels.items():
            label.setText(self._manager.mouse_binding_text(binding_id))

    def _refresh_sequences(self) -> None:
        # Compatibility for older tests and callers.
        self._refresh_bindings()
