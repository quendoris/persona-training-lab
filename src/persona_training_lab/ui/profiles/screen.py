from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from persona_training_lab.ui.components.cards import PanelCard
from persona_training_lab.ui.components.metrics import TraitMetricCard
from persona_training_lab.ui.components.panels import make_muted_label
from persona_training_lab.ui.viewmodels.profiles import ProfilesViewModel


def _elide(text: str, max_len: int = 42) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


class ProfileEditorDialog(QDialog):
    def __init__(self, *, parent: QWidget | None, title: str, initial: dict[str, str]) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(560, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._title = QLineEdit(initial.get("title", ""))
        self._description = QTextEdit(initial.get("description", ""))
        self._communication_style = QTextEdit(initial.get("communication_style", ""))
        self._principles = QTextEdit(initial.get("principles", ""))
        self._constraints = QTextEdit(initial.get("constraints", ""))
        self._notes = QTextEdit(initial.get("notes", ""))

        fields = [
            ("Название", self._title),
            ("Краткое описание", self._description),
            ("Стиль общения", self._communication_style),
            ("Принципы", self._principles),
            ("Ограничения", self._constraints),
            ("Заметки", self._notes),
        ]
        for label_text, widget in fields:
            layout.addWidget(make_muted_label(label_text))
            layout.addWidget(widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def payload(self) -> dict[str, str]:
        return {
            "title": self._title.text(),
            "description": self._description.toPlainText(),
            "communication_style": self._communication_style.toPlainText(),
            "principles": self._principles.toPlainText(),
            "constraints": self._constraints.toPlainText(),
            "notes": self._notes.toPlainText(),
        }


class ProfilesScreen(QWidget):
    def __init__(self, view_model: ProfilesViewModel) -> None:
        super().__init__()
        self._vm = view_model

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)
        self._title = QLabel("Профили личности")
        self._title.setObjectName("ScreenTitle")
        self._subtitle = make_muted_label("Целевые структуры personality, а не просто стилистические маски.")
        header_layout.addWidget(self._title)
        header_layout.addWidget(self._subtitle)
        root.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left_container = QWidget()
        left_container.setFixedWidth(360)
        left = QVBoxLayout(left_container)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(16)
        body.addWidget(left_container, 0)

        self._profiles_card = PanelCard("Реестр профилей", "Тот самый слой, где мы закрепляем ядро личности.")
        controls = QHBoxLayout()
        controls.setSpacing(8)

        create_btn = QPushButton("Создать")
        create_btn.setObjectName("SecondaryButton")
        create_btn.clicked.connect(self._on_create_profile)
        controls.addWidget(create_btn)

        edit_btn = QPushButton("Редактировать")
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.clicked.connect(self._on_edit_profile)
        controls.addWidget(edit_btn)
        self._edit_btn = edit_btn

        self._profiles_card._layout.addLayout(controls)

        self._profiles_list = QListWidget()
        self._profiles_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._profiles_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._profiles_list.setUniformItemSizes(True)
        self._profiles_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._profiles_list.itemSelectionChanged.connect(self._on_profile_changed)
        self._profiles_card.add_widget(self._profiles_list)
        left.addWidget(self._profiles_card, 1)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        self._summary_card = PanelCard("Суть профиля", "Что мы хотим сформировать в модели и чего не хотим потерять.")
        self._summary_text = make_muted_label("")
        self._summary_card.add_widget(self._summary_text)
        self._constraints_wrap = QVBoxLayout()
        self._constraints_wrap.setSpacing(10)
        self._summary_card._layout.addLayout(self._constraints_wrap)
        center.addWidget(self._summary_card, 0)

        self._traits_card = PanelCard("Карта черт", "Черты как опорные оси, а не абстрактные слова.")
        self._traits_card.setMaximumHeight(430)
        self._traits_grid = QGridLayout()
        self._traits_grid.setSpacing(12)
        self._traits_card._layout.addLayout(self._traits_grid)
        center.addWidget(self._traits_card, 0)
        center.addStretch(1)

        right_container = QWidget()
        right_container.setFixedWidth(330)
        right = QVBoxLayout(right_container)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(16)
        body.addWidget(right_container, 0)

        self._linked_card = PanelCard("Связанные артефакты", "Профиль живёт вместе с данными, training и snapshot-ветками.")
        self._linked_layout = QVBoxLayout()
        self._linked_layout.setSpacing(10)
        self._linked_card._layout.addLayout(self._linked_layout)
        right.addWidget(self._linked_card)

        self._next_card = PanelCard("Следующий лучший шаг", "Система должна не просто показывать профиль, а вести дальше.")
        self._next_text = make_muted_label("")
        self._next_card.add_widget(self._next_text)
        right.addWidget(self._next_card)
        right.addStretch(1)

        self._populate_profiles()
        self._refresh_all()

    def _populate_profiles(self) -> None:
        self._profiles_list.clear()
        current_id = self._vm.current_profile().profile_id
        current_item = None
        for profile_id, title, _subtitle in self._vm.profiles():
            item = QListWidgetItem(_elide(title))
            item.setToolTip(title)
            item.setData(Qt.ItemDataRole.UserRole, profile_id)
            self._profiles_list.addItem(item)
            if profile_id == current_id:
                current_item = item
        if current_item is not None:
            self._profiles_list.setCurrentItem(current_item)
        self._edit_btn.setEnabled(self._vm.current_profile().profile_id not in {"profiles_empty", "profiles_error"})

    def _refresh_header(self) -> None:
        title, subtitle = self._vm.header_summary()
        self._title.setText(f"Профили · {title}")
        self._subtitle.setText(subtitle)

    def _refresh_summary(self) -> None:
        profile = self._vm.current_profile()
        self._summary_text.setText(profile.summary)
        while self._constraints_wrap.count():
            item = self._constraints_wrap.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for text in profile.constraints:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(10)
            icon = QLabel("")
            icon.setObjectName("LineageIcon")
            icon.setAlignment(Qt.AlignCenter)
            icon.setFixedSize(24, 24)
            layout.addWidget(icon)
            layout.addWidget(make_muted_label(text), 1)
            self._constraints_wrap.addWidget(row)

    def _refresh_traits(self) -> None:
        while self._traits_grid.count():
            item = self._traits_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for index, trait in enumerate(self._vm.current_profile().traits):
            card = TraitMetricCard(title=trait.name, value=trait.target, note=trait.note)
            self._traits_grid.addWidget(card, index // 2, index % 2)

    def _refresh_linked(self) -> None:
        while self._linked_layout.count():
            item = self._linked_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for text in self._vm.current_profile().linked_artifacts:
            row = QFrame()
            row.setObjectName("LineageRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(10)
            icon = QLabel("")
            icon.setObjectName("LineageIcon")
            icon.setAlignment(Qt.AlignCenter)
            icon.setFixedSize(24, 24)
            layout.addWidget(icon)
            link_label = QLabel(_elide(text, 34))
            link_label.setToolTip(text)
            layout.addWidget(link_label, 1)
            self._linked_layout.addWidget(row)
        profile = self._vm.current_profile()
        if profile.profile_id in {"profiles_empty", "profiles_error"}:
            self._next_text.setText("Создайте профиль личности и затем переходите к подготовке обучения.")
        else:
            self._next_text.setText("Профиль сохранён. Теперь можно привязать датасет и создать запуск обучения.")

    def _refresh_all(self) -> None:
        self._refresh_header()
        self._refresh_summary()
        self._refresh_traits()
        self._refresh_linked()

    def _on_profile_changed(self) -> None:
        item = self._profiles_list.currentItem()
        if item is None:
            return
        self._vm.select_profile(item.data(Qt.ItemDataRole.UserRole))
        self._edit_btn.setEnabled(self._vm.current_profile().profile_id not in {"profiles_empty", "profiles_error"})
        self._refresh_all()

    def _on_create_profile(self) -> None:
        dialog = ProfileEditorDialog(parent=self, title="Создать профиль", initial=self._vm.profile_form_data())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        ok, _message = self._vm.create_profile(**dialog.payload())
        self._populate_profiles()
        self._refresh_all()
        if not ok:
            self._subtitle.setText(_message)

    def _on_edit_profile(self) -> None:
        if self._vm.current_profile().profile_id in {"profiles_empty", "profiles_error"}:
            return
        dialog = ProfileEditorDialog(parent=self, title="Редактировать профиль", initial=self._vm.profile_form_data())
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        ok, _message = self._vm.update_current_profile(**dialog.payload())
        self._populate_profiles()
        self._refresh_all()
        if not ok:
            self._subtitle.setText(_message)
