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
from persona_training_lab.ui.components.panels import (
    make_muted_label,
    make_status_label,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.i18n.text import text as localized_text
from persona_training_lab.ui.viewmodels.profiles import (
    ProfileText,
    ProfilesViewModel,
)


def _elide(text: str, max_len: int = 42) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


class ProfileEditorDialog(QDialog):
    def __init__(
        self,
        *,
        parent: QWidget | None,
        title_key: str,
        initial: dict[str, str],
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__(parent)
        self._localization = localization
        self._title_key = title_key
        self.setModal(True)
        self.resize(640, 660)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self._hint = make_muted_label("")
        layout.addWidget(self._hint)

        self._title = QLineEdit(initial.get("title", ""))
        self._description = QTextEdit(initial.get("description", ""))
        self._communication_style = QTextEdit(
            initial.get("communication_style", "")
        )
        self._principles = QTextEdit(initial.get("principles", ""))
        self._constraints = QTextEdit(initial.get("constraints", ""))
        self._notes = QTextEdit(initial.get("notes", ""))

        fields = (
            ("profiles.field.title", self._title),
            ("profiles.field.description", self._description),
            (
                "profiles.field.communication_style",
                self._communication_style,
            ),
            ("profiles.field.principles", self._principles),
            ("profiles.field.constraints", self._constraints),
            ("profiles.field.notes", self._notes),
        )
        self._field_labels: list[tuple[QLabel, str]] = []
        for key, widget in fields:
            label = make_muted_label("")
            self._field_labels.append((label, key))
            layout.addWidget(label)
            layout.addWidget(widget)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._apply_language()
        if localization is not None:
            localization.language_changed.connect(self._apply_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _apply_language(self, _locale: str = "") -> None:
        self.setWindowTitle(self._text(self._title_key))
        self._hint.setText(self._text("profiles.dialog.hint"))
        self._title.setPlaceholderText(
            self._text("profiles.placeholder.title")
        )
        self._description.setPlaceholderText(
            self._text("profiles.placeholder.description")
        )
        self._communication_style.setPlaceholderText(
            self._text("profiles.placeholder.communication_style")
        )
        self._principles.setPlaceholderText(
            self._text("profiles.placeholder.principles")
        )
        self._constraints.setPlaceholderText(
            self._text("profiles.placeholder.constraints")
        )
        self._notes.setPlaceholderText(
            self._text("profiles.placeholder.notes")
        )
        for label, key in self._field_labels:
            label.setText(self._text(key))
        save_button = self._buttons.button(
            QDialogButtonBox.StandardButton.Save
        )
        cancel_button = self._buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        if save_button is not None:
            save_button.setText(self._text("common.save"))
        if cancel_button is not None:
            cancel_button.setText(self._text("common.cancel"))

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
    def __init__(
        self,
        view_model: ProfilesViewModel,
        localization: LocalizationManager | None = None,
    ) -> None:
        super().__init__()
        self._vm = view_model
        self._localization = localization

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("ShellHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 20, 22, 20)
        header_layout.setSpacing(8)
        self._title = QLabel()
        self._title.setObjectName("ScreenTitle")
        self._subtitle = make_muted_label("")
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

        self._profiles_card = PanelCard("", "")
        controls = QHBoxLayout()
        controls.setSpacing(8)

        self._create_btn = QPushButton()
        self._create_btn.setObjectName("SecondaryButton")
        self._create_btn.clicked.connect(self._on_create_profile)
        controls.addWidget(self._create_btn)

        self._edit_btn = QPushButton()
        self._edit_btn.setObjectName("SecondaryButton")
        self._edit_btn.clicked.connect(self._on_edit_profile)
        controls.addWidget(self._edit_btn)
        self._profiles_card._layout.addLayout(controls)

        self._profiles_list = QListWidget()
        self._profiles_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._profiles_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._profiles_list.setUniformItemSizes(True)
        self._profiles_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._profiles_list.itemSelectionChanged.connect(
            self._on_profile_changed
        )
        self._profiles_card.add_widget(self._profiles_list)
        left.addWidget(self._profiles_card, 1)

        center = QVBoxLayout()
        center.setSpacing(16)
        body.addLayout(center, 4)

        self._summary_card = PanelCard("", "")
        self._readiness_badge = make_status_label("")
        self._summary_card.add_widget(self._readiness_badge)
        self._summary_text = make_muted_label("")
        self._summary_card.add_widget(self._summary_text)
        self._constraints_wrap = QVBoxLayout()
        self._constraints_wrap.setSpacing(10)
        self._summary_card._layout.addLayout(self._constraints_wrap)
        center.addWidget(self._summary_card, 0)

        self._traits_card = PanelCard("", "")
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

        self._linked_card = PanelCard("", "")
        self._linked_layout = QVBoxLayout()
        self._linked_layout.setSpacing(10)
        self._linked_card._layout.addLayout(self._linked_layout)
        right.addWidget(self._linked_card)

        self._next_card = PanelCard("", "")
        self._next_text = make_muted_label("")
        self._next_card.add_widget(self._next_text)
        right.addWidget(self._next_card)
        right.addStretch(1)

        self._apply_static_text()
        self._populate_profiles()
        self._refresh_all()
        if localization is not None:
            localization.language_changed.connect(self._refresh_language)

    def _text(self, key: str, **values: object) -> str:
        return localized_text(self._localization, key, **values)

    def _render(self, value: object) -> str:
        if isinstance(value, ProfileText):
            rendered_values = {
                key: self._render(item)
                if isinstance(item, ProfileText)
                else item
                for key, item in value.values.items()
            }
            return self._text(value.key, **rendered_values)
        return str(value)

    def _apply_static_text(self) -> None:
        self._create_btn.setText(self._text("profiles.action.create"))
        self._edit_btn.setText(self._text("profiles.action.edit"))
        self._profiles_card.set_title(
            self._text("profiles.card.registry.title")
        )
        self._profiles_card.set_subtitle(
            self._text("profiles.card.registry.description")
        )
        self._summary_card.set_title(
            self._text("profiles.card.summary.title")
        )
        self._summary_card.set_subtitle(
            self._text("profiles.card.summary.description")
        )
        self._traits_card.set_title(
            self._text("profiles.card.readiness.title")
        )
        self._traits_card.set_subtitle(
            self._text("profiles.card.readiness.description")
        )
        self._linked_card.set_title(
            self._text("profiles.card.linked.title")
        )
        self._linked_card.set_subtitle(
            self._text("profiles.card.linked.description")
        )
        self._next_card.set_title(
            self._text("profiles.card.next.title")
        )
        self._next_card.set_subtitle(
            self._text("profiles.card.next.description")
        )
        self._readiness_badge.setText(
            self._text("profiles.badge.structure")
        )

    def _refresh_language(self, _locale: str = "") -> None:
        self._apply_static_text()
        self._populate_profiles()
        self._refresh_all()

    def _populate_profiles(self) -> None:
        self._profiles_list.clear()
        current_id = self._vm.current_profile().profile_id
        current_item = None
        for profile in self._vm.profile_views():
            title = self._render(profile.title)
            item = QListWidgetItem(_elide(title))
            item.setToolTip(title)
            item.setData(Qt.ItemDataRole.UserRole, profile.profile_id)
            self._profiles_list.addItem(item)
            if profile.profile_id == current_id:
                current_item = item
        if current_item is not None:
            self._profiles_list.setCurrentItem(current_item)
        self._edit_btn.setEnabled(
            self._vm.current_profile().profile_id
            not in {"profiles_empty", "profiles_error"}
        )

    def _refresh_header(self) -> None:
        title, subtitle = self._vm.header_summary_model()
        self._title.setText(
            self._text("profiles.header.title", title=self._render(title))
        )
        self._subtitle.setText(self._render(subtitle))

    def _refresh_summary(self) -> None:
        profile = self._vm.current_profile()
        self._summary_text.setText(self._render(profile.summary))
        while self._constraints_wrap.count():
            item = self._constraints_wrap.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for value in profile.constraints:
            row = QFrame()
            row.setObjectName("PanelCardSoft")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(10)
            icon = QLabel("")
            icon.setObjectName("LineageIcon")
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedSize(24, 24)
            layout.addWidget(icon)
            layout.addWidget(make_muted_label(self._render(value)), 1)
            self._constraints_wrap.addWidget(row)

    def _refresh_traits(self) -> None:
        while self._traits_grid.count():
            item = self._traits_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for index, trait in enumerate(self._vm.current_profile().traits):
            card = TraitMetricCard(
                title=self._render(trait.name),
                value=trait.target,
                note=self._render(trait.note),
            )
            self._traits_grid.addWidget(card, index // 2, index % 2)

    def _refresh_linked(self) -> None:
        while self._linked_layout.count():
            item = self._linked_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for value in self._vm.current_profile().linked_artifacts:
            text = self._render(value)
            row = QFrame()
            row.setObjectName("LineageRow")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(10)
            icon = QLabel("")
            icon.setObjectName("LineageIcon")
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon.setFixedSize(24, 24)
            layout.addWidget(icon)
            link_label = QLabel(_elide(text, 34))
            link_label.setToolTip(text)
            layout.addWidget(link_label, 1)
            self._linked_layout.addWidget(row)
        self._next_text.setText(self._render(self._vm.next_step_model()))

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
        self._edit_btn.setEnabled(
            self._vm.current_profile().profile_id
            not in {"profiles_empty", "profiles_error"}
        )
        self._refresh_all()

    def _on_create_profile(self) -> None:
        dialog = ProfileEditorDialog(
            parent=self,
            title_key="profiles.dialog.create.title",
            initial=self._vm.profile_form_data(),
            localization=self._localization,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._vm.create_profile(**dialog.payload())
        self._populate_profiles()
        self._refresh_all()
        message = self._vm.current_message()
        if message is not None:
            self._subtitle.setText(self._render(message))

    def _on_edit_profile(self) -> None:
        if self._vm.current_profile().profile_id in {
            "profiles_empty",
            "profiles_error",
        }:
            return
        dialog = ProfileEditorDialog(
            parent=self,
            title_key="profiles.dialog.edit.title",
            initial=self._vm.profile_form_data(),
            localization=self._localization,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._vm.update_current_profile(**dialog.payload())
        self._populate_profiles()
        self._refresh_all()
        message = self._vm.current_message()
        if message is not None:
            self._subtitle.setText(self._render(message))
