from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QDialogButtonBox

from persona_training_lab.application.messages import ActionResult
from persona_training_lab.application.profiles.service import ProfileSummary
from persona_training_lab.i18n.audit import SourceAudit
from persona_training_lab.i18n.deep_audit import DeepSurfaceAudit
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
        return ActionResult(False, "communication_style_required"), None


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


def test_profile_validation_message_has_semantic_key(tmp_path: Path) -> None:
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

    profile_source = """
_LEGACY_TEMPLATES = {
    "profiles.message.created": "Duplicated profile presentation copy",
}


class ProfileStatus:
    READY = "готов"


def create_profile():
    hidden = {"status": "готов"}
    semantic = {"status": "ready"}
    return False, "Hidden profile create result", hidden, semantic


def update_profile():
    status = "готов"
    hidden = {"status": status}
    semantic = {"status": "ready"}
    return False, "Hidden profile update result", hidden, semantic


def render_profile():
    hidden_trait = TraitView(
        "Hidden profile trait",
        0,
        "Hidden profile trait note",
    )
    semantic_trait = TraitView(
        profile_text("profiles.trait.description"),
        0,
        profile_text("profiles.trait.required"),
    )
    hidden_profile = ProfileView(
        profile_id="profile",
        title="Raw profile title",
        subtitle="Raw profile subtitle",
        summary="Raw profile summary",
        communication_style="Raw user style",
        principles_text="Raw user principle",
        constraints_text="Raw user constraint",
        notes="Raw user note",
        constraints=("Raw user constraint",),
        linked_artifacts=("Hidden profile linked artifact",),
        traits=(semantic_trait,),
        readiness="Hidden profile readiness",
        readiness_code="ready",
        completeness=100,
        status_code="ready",
    )
    semantic_profile = ProfileView(
        profile_id="profile",
        title="Raw profile title",
        subtitle="Raw profile subtitle",
        summary="Raw profile summary",
        communication_style="Raw user style",
        principles_text="Raw user principle",
        constraints_text="Raw user constraint",
        notes="Raw user note",
        constraints=("Raw user constraint",),
        linked_artifacts=(profile_text("profiles.link.status"),),
        traits=(semantic_trait,),
        readiness=profile_text("profiles.readiness.percent"),
        readiness_code="ready",
        completeness=100,
        status_code="ready",
    )
    return hidden_trait, hidden_profile, semantic_profile
"""
    path = tmp_path / "ui" / "viewmodels" / "profiles_sample.py"
    path.parent.mkdir(parents=True)
    deep_visitor = DeepSurfaceAudit(path, display_root=tmp_path)
    deep_visitor.visit(ast.parse(profile_source, filename=str(path)))
    findings = {(item.call, item.text) for item in deep_visitor.literals}

    assert (
        "forbidden presentation catalog",
        "_LEGACY_TEMPLATES",
    ) in findings
    assert ("ProfileStatus code", "готов") in findings
    assert ("create_profile persisted status", "готов") in findings
    assert (
        "create_profile return",
        "Hidden profile create result",
    ) in findings
    assert ("update_profile persisted status", "готов") in findings
    assert (
        "update_profile return",
        "Hidden profile update result",
    ) in findings
    assert ("TraitView name", "Hidden profile trait") in findings
    assert ("TraitView note", "Hidden profile trait note") in findings
    assert (
        "ProfileView linked_artifacts",
        "Hidden profile linked artifact",
    ) in findings
    assert (
        "ProfileView readiness",
        "Hidden profile readiness",
    ) in findings
    assert not any(text == "ready" for _, text in findings)
    assert not any(text == "Raw user style" for _, text in findings)
    assert not any(text == "Raw user constraint" for _, text in findings)
    assert not any(
        text == "profiles.trait.description" for _, text in findings
    )
    assert not any(text == "profiles.link.status" for _, text in findings)

    source_visitor = SourceAudit(
        path,
        known_keys=frozenset({"profiles.message.created"}),
    )
    source_visitor.visit(
        ast.parse(
            """
_PROFILE_ACTION_KEYS = {
    "known": "profiles.message.created",
    "missing": "missing.profile.map.key",
    "machine": "save_failed",
}
profile_text("profiles.message.created")
profile_text("missing.profile.constructor")
""",
            filename=str(path),
        )
    )
    assert source_visitor.translation_keys == {
        "profiles.message.created",
        "missing.profile.map.key",
        "missing.profile.constructor",
    }
    assert "save_failed" not in source_visitor.translation_keys
