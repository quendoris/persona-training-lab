from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QAbstractScrollArea,
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
from persona_training_lab.ui.keybindings.manager import BindingChangeResult, KeyBindingManager


class _ShortcutCaptureDialog(QDialog):
    def __init__(self, title: str, current_sequence: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Изменить сочетание")
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        heading = QLabel(title)
        heading.setObjectName("CardTitle")
        root.addWidget(heading)
        root.addWidget(make_muted_label("Нажмите новое сочетание. Оно будет применено сразу после сохранения."))

        current = QKeySequence.fromString(current_sequence, QKeySequence.SequenceFormat.PortableText)
        self._editor = QKeySequenceEdit(current)
        if hasattr(self._editor, "setMaximumSequenceLength"):
            self._editor.setMaximumSequenceLength(1)
        if hasattr(self._editor, "setClearButtonEnabled"):
            self._editor.setClearButtonEnabled(True)
        root.addWidget(self._editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
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

    def sequence(self) -> str:
        return self._editor.keySequence().toString(QKeySequence.SequenceFormat.PortableText)


class KeyBindingsScreen(QWidget):
    def __init__(self, manager: KeyBindingManager) -> None:
        super().__init__()
        self._manager = manager
        self._sequence_labels: dict[str, QLabel] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        header = PanelCard(
            "Назначения клавиш",
            "Горячие клавиши применяются сразу, проверяются на конфликты и сохраняются между запусками.",
        )
        header_actions = QWidget()
        header_actions.setProperty("transparentBg", True)
        header_actions_layout = QHBoxLayout(header_actions)
        header_actions_layout.setContentsMargins(0, 0, 0, 0)
        header_actions_layout.setSpacing(10)
        path_label = make_muted_label(str(self._manager.storage_path))
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
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
        scroll.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        content = QWidget()
        content.setProperty("transparentBg", True)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        bindings_title = QLabel("Клавиатура")
        bindings_title.setObjectName("SectionTitle")
        content_layout.addWidget(bindings_title)
        for definition in self._manager.definitions():
            content_layout.addWidget(self._binding_card(definition.binding_id))

        guide_title = QLabel("Мышь и canvas")
        guide_title.setObjectName("SectionTitle")
        content_layout.addWidget(guide_title)
        for guide in self._manager.fixed_input_guide():
            content_layout.addWidget(self._guide_card(guide.gesture, guide.title, guide.description))

        content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self._manager.bindings_changed.connect(self._refresh_sequences)
        self._refresh_sequences()

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
        edit.clicked.connect(lambda _checked=False, item_id=binding_id: self._edit_binding(item_id))
        reset = QPushButton("По умолчанию")
        reset.setObjectName("SecondaryButton")
        reset.clicked.connect(lambda _checked=False, item_id=binding_id: self._reset_binding(item_id))

        layout.addWidget(sequence, 0)
        layout.addStretch(1)
        layout.addWidget(edit, 0)
        layout.addWidget(reset, 0)
        card.add_widget(row)
        return card

    @staticmethod
    def _guide_card(gesture: str, title: str, description: str) -> QWidget:
        card = PanelCard(title, description)
        gesture_label = QLabel(gesture)
        gesture_label.setObjectName("TelemetryChip")
        gesture_label.setWordWrap(True)
        card.add_widget(gesture_label)
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
        result = self._manager.set_sequence(binding_id, dialog.sequence())
        self._handle_result(result)

    def _reset_binding(self, binding_id: str) -> None:
        result = self._manager.reset_binding(binding_id)
        self._handle_result(result)

    def _reset_all(self) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle("Вернуть стандартные назначения?")
        dialog.setText("Все изменённые сочетания будут заменены значениями по умолчанию.")
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
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

    def _handle_result(self, result: BindingChangeResult) -> None:
        if result.accepted:
            return
        if result.conflict_title:
            self._show_message(
                "Конфликт сочетаний",
                f"Это сочетание уже назначено команде «{result.conflict_title}». Выберите другое.",
                QMessageBox.Icon.Warning,
            )
            return
        self._show_message("Не удалось изменить назначение", result.error, QMessageBox.Icon.Warning)

    def _show_message(self, title: str, text: str, icon: QMessageBox.Icon) -> None:
        dialog = QMessageBox(self)
        dialog.setIcon(icon)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        ok = dialog.button(QMessageBox.StandardButton.Ok)
        if ok is not None:
            ok.setText("Понятно")
        dialog.exec()

    def _refresh_sequences(self) -> None:
        for binding_id, label in self._sequence_labels.items():
            label.setText(self._manager.sequence(binding_id) or "Не назначено")
