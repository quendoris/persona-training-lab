from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from persona_training_lab.i18n.catalog import (
    CatalogSet,
    CatalogValidationError,
)
from persona_training_lab.ui.i18n.manager import LocalizationManager


CATALOGS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "persona_training_lab"
    / "i18n"
    / "catalogs"
)


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_repository_catalogs_are_complete_and_placeholder_safe() -> None:
    catalogs = CatalogSet.load(CATALOGS, base_locale="ru-RU")

    assert catalogs.available_locales() == ("en-US", "ru-RU")
    assert catalogs.catalog("ru-RU").text(
        "language.unavailable_incomplete",
        values={"locale": "en-US"},
    ) == "Язык en-US недоступен: перевод не завершён."
    assert catalogs.catalog("en-US").text(
        "operations.active_count",
        count=1,
    ) == "1 active operation"
    assert catalogs.catalog("en-US").text(
        "operations.active_count",
        count=2,
    ) == "2 active operations"
    assert catalogs.catalog("ru-RU").text(
        "operations.active_count",
        count=22,
    ) == "22 активные операции"


def test_catalog_set_rejects_missing_keys_and_placeholder_drift(
    tmp_path: Path,
) -> None:
    base = {
        "meta": {
            "schema": 1,
            "locale": "ru-RU",
            "name": "Russian",
            "native_name": "Русский",
            "direction": "ltr",
        },
        "messages": {
            "message": "Ошибка {error_id}",
            "other": "Готово",
        },
    }
    translated = {
        "meta": {
            "schema": 1,
            "locale": "en-US",
            "name": "English",
            "native_name": "English",
            "direction": "ltr",
        },
        "messages": {
            "message": "Error {id}",
        },
    }
    (tmp_path / "ru-RU.json").write_text(
        json.dumps(base, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "en-US.json").write_text(
        json.dumps(translated, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(CatalogValidationError):
        CatalogSet.load(tmp_path, base_locale="ru-RU")


def test_live_binding_switches_atomically_without_widget_rebuild(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=CATALOGS,
    )
    label = QLabel()
    manager.bind_text(label, "nav.agents")

    assert label.text() == "Agents"
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    manager.set_locale("ru-RU", persist=False)

    assert label.text() == "Агенты"
    assert manager.locale == "ru-RU"
    label.deleteLater()
    app.processEvents()


def test_complete_third_locale_is_discovered_without_python_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for locale in ("ru-RU", "en-US"):
        payload = json.loads(
            (CATALOGS / f"{locale}.json").read_text(encoding="utf-8")
        )
        (tmp_path / f"{locale}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    spanish = json.loads(
        (CATALOGS / "en-US.json").read_text(encoding="utf-8")
    )
    spanish["meta"] = {
        "schema": 1,
        "locale": "es-ES",
        "name": "Spanish",
        "native_name": "Español",
        "direction": "ltr",
    }
    spanish["messages"]["nav.agents"] = "Agentes"
    spanish["messages"]["operations.active_count"] = {
        "one": "{count} operación activa",
        "other": "{count} operaciones activas",
    }
    (tmp_path / "es-ES.json").write_text(
        json.dumps(spanish, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    app = _app()
    manager = LocalizationManager(
        app,
        initial_locale="en-US",
        catalog_directory=tmp_path,
    )
    monkeypatch.setattr(manager, "_prepare_qt_translator", lambda _locale: None)
    label = QLabel()
    manager.bind_text(label, "nav.agents")

    assert manager.available_locales() == ("en-US", "es-ES", "ru-RU")
    manager.set_locale("es-ES", persist=False)
    assert label.text() == "Agentes"
    assert manager.text("operations.active_count", count=1) == "1 operación activa"
    assert manager.text("operations.active_count", count=3) == "3 operaciones activas"

    label.deleteLater()
    app.processEvents()


def test_unknown_locale_or_key_never_falls_back_silently() -> None:
    catalogs = CatalogSet.load(CATALOGS, base_locale="ru-RU")

    with pytest.raises(CatalogValidationError):
        catalogs.catalog("de-DE")
    with pytest.raises(CatalogValidationError):
        catalogs.catalog("en-US").text("missing.key")
