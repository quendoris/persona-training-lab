from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from persona_training_lab.application.profiles.service import ProfileSummary
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.profiles.screen import (
    ProfileEditorDialog,
    ProfilesScreen,
)
from persona_training_lab.ui.viewmodels.profiles import ProfilesViewModel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _manager(app: QApplication) -> LocalizationManager:
    return LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )


def _flush_deferred_deletes() -> None:
    QCoreApplication.sendPostedEvents(
        None,
        QEvent.Type.DeferredDelete,
    )


class EmptyProfilesService:
    def list_profiles(self) -> list[ProfileSummary]:
        return []


class LegacyRussianProfileService:
    def list_profiles(self) -> list[ProfileSummary]:
        return [
            ProfileSummary(
                profile_id="mia_core",
                title="Mia core",
                subtitle="Legacy profile",
                description="Stable personality foundation",
                communication_style="Warm and direct",
                principles="Continuity\nHonesty",
                constraints="Do not lose the core",
                notes="",
                status="активен",
            )
        ]


class ValidationFailureProfilesService(EmptyProfilesService):
    def create_profile(self, **_payload):
        return False, "Стиль общения не должен быть пустым", None


def test_profiles_empty_workspace_switches_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    screen = ProfilesScreen(
        ProfilesViewModel(profiles_service=EmptyProfilesService()),
        manager,
    )
    screen.show()
    app.processEvents()

    assert screen._title.text() == "Profiles · No profiles yet"
    assert screen._create_btn.text() == "Create"
    assert screen._edit_btn.text() == "Edit"
    assert screen._profiles_card.title_label.text() == "Profile registry"
    assert screen._summary_text.text() == (
        "No personality profiles have been created yet."
    )
    assert screen._readiness_badge.text() == (
        "Profile structure is incomplete"
    )
    assert screen._next_text.text() == (
        "Create a personality profile, then prepare and approve a dataset."
    )

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    assert screen._title.text() == "Профили · Профили пока не созданы"
    assert screen._create_btn.text() == "Создать"
    assert screen._edit_btn.text() == "Редактировать"
    assert screen._profiles_card.title_label.text() == "Реестр профилей"
    assert screen._summary_text.text() == (
        "Профили личности пока не созданы."
    )
    assert screen._readiness_badge.text() == (
        "Структура профиля не заполнена"
    )
    assert screen._next_text.text() == (
        "Создайте профиль личности, затем подготовьте и одобрите датасет."
    )

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_legacy_profile_status_is_rendered_in_current_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    vm = ProfilesViewModel(
        profiles_service=LegacyRussianProfileService()
    )
    screen = ProfilesScreen(vm, manager)
    screen.show()
    app.processEvents()

    linked_texts = {
        screen._linked_layout.itemAt(index).widget().findChildren(
            type(screen._title)
        )[-1].text()
        for index in range(screen._linked_layout.count())
    }
    assert "Status · active" in linked_texts
    assert all("активен" not in text for text in linked_texts)
    assert screen._readiness_badge.text() == "Profile structure: 100%"
    assert vm.current_profile().status_code == "active"
    assert vm.current_profile().readiness_code == "ready"

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()
    _flush_deferred_deletes()
    app.processEvents()

    linked_texts = {
        screen._linked_layout.itemAt(index).widget().findChildren(
            type(screen._title)
        )[-1].text()
        for index in range(screen._linked_layout.count())
    }
    assert "Статус · активен" in linked_texts
    assert screen._readiness_badge.text() == "Структура профиля: 100%"

    screen.close()
    screen.deleteLater()
    app.processEvents()


def test_profile_editor_switches_title_fields_and_buttons_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = _manager(app)
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    dialog = ProfileEditorDialog(
        parent=None,
        title_key="profiles.dialog.create.title",
        initial={},
        localization=manager,
    )
    dialog.show()
    app.processEvents()

    save_button = dialog._buttons.button(
        QDialogButtonBox.StandardButton.Save
    )
    cancel_button = dialog._buttons.button(
        QDialogButtonBox.StandardButton.Cancel
    )
    assert save_button is not None
    assert cancel_button is not None
    assert dialog.windowTitle() == "Create profile"
    assert dialog._title.placeholderText() == "For example: Persona core v1"
    assert save_button.text() == "Save"
    assert cancel_button.text() == "Cancel"

    manager.set_locale("ru-RU", persist=False)
    app.processEvents()

    assert dialog.windowTitle() == "Создать профиль"
    assert dialog._title.placeholderText() == "Например: Persona core v1"
    assert save_button.text() == "Сохранить"
    assert cancel_button.text() == "Отмена"

    dialog.close()
    dialog.deleteLater()
    app.processEvents()


def test_profile_validation_message_has_semantic_key() -> None:
    vm = ProfilesViewModel(
        profiles_service=ValidationFailureProfilesService()
    )

    ok, legacy = vm.create_profile(
        title="Core",
        description="Description",
        communication_style="",
        principles="Principle",
        constraints="Constraint",
        notes="",
    )

    message = vm.current_message()
    assert ok is False
    assert legacy == "Стиль общения не должен быть пустым"
    assert message is not None
    assert message.key == "profiles.validation.communication_style_required"
