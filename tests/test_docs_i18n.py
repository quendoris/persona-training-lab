from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from persona_training_lab.application.docs.service import DocsService
from persona_training_lab.ui.docs.screen import DocsScreen
from persona_training_lab.ui.i18n.manager import LocalizationManager
from persona_training_lab.ui.viewmodels.docs import DocsViewModel


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_docs_workspace_switches_metadata_without_losing_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    vm = DocsViewModel(DocsService(root=Path.cwd()))
    screen = DocsScreen(vm, manager)

    screen._topic_list.setCurrentRow(2)
    body = screen._content.toPlainText()

    assert screen._topics_card.title_label.text() == "Documentation"
    assert screen._topic_list.currentRow() == 2
    assert screen._topic_list.currentItem().text() == "Personality portrait"
    assert screen._title.text() == "Personality portrait"
    assert "Big Five KPI" in screen._summary.text()
    assert body

    manager.set_locale("ru-RU", persist=False)

    assert screen._topics_card.title_label.text() == "Документация"
    assert screen._topic_list.currentRow() == 2
    assert screen._topic_list.currentItem().text() == "Портрет личности"
    assert screen._title.text() == "Портрет личности"
    assert "Big Five KPI" in screen._summary.text()
    assert screen._content.toPlainText() == body

    manager.set_locale("en-US", persist=False)

    assert screen._topic_list.currentRow() == 2
    assert screen._topic_list.currentItem().text() == "Personality portrait"
    assert screen._content.toPlainText() == body

    screen.deleteLater()
    app.processEvents()
