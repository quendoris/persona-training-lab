from __future__ import annotations

import json
from pathlib import Path

import pytest

from persona_training_lab.i18n.catalog import (
    CatalogSet,
    CatalogValidationError,
)


def _write_root(
    directory: Path,
    locale: str,
    *,
    name: str,
    native_name: str,
) -> None:
    payload = {
        "meta": {
            "schema": 1,
            "locale": locale,
            "name": name,
            "native_name": native_name,
            "direction": "ltr",
        },
        "messages": {"base.message": locale},
    }
    (directory / f"{locale}.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_fragment(
    directory: Path,
    locale: str,
    fragment: str,
    messages: dict[str, object],
) -> None:
    locale_directory = directory / locale
    locale_directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "schema": 1,
            "locale": locale,
            "fragment": fragment,
        },
        "messages": messages,
    }
    (locale_directory / f"{fragment}.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_catalog_set_merges_complete_locale_fragments(tmp_path: Path) -> None:
    _write_root(tmp_path, "ru-RU", name="Russian", native_name="Русский")
    _write_root(tmp_path, "en-US", name="English", native_name="English")
    _write_fragment(
        tmp_path,
        "ru-RU",
        "dashboard",
        {"dashboard.title": "Панель"},
    )
    _write_fragment(
        tmp_path,
        "en-US",
        "dashboard",
        {"dashboard.title": "Dashboard"},
    )

    catalogs = CatalogSet.load(tmp_path, base_locale="ru-RU")

    assert catalogs.catalog("ru-RU").text("dashboard.title") == "Панель"
    assert catalogs.catalog("en-US").text("dashboard.title") == "Dashboard"


def test_third_locale_with_fragments_needs_no_python_changes(
    tmp_path: Path,
) -> None:
    locales = (
        ("ru-RU", "Russian", "Русский", "Панель"),
        ("en-US", "English", "English", "Dashboard"),
        ("es-ES", "Spanish", "Español", "Panel de control"),
    )
    for locale, name, native_name, title in locales:
        _write_root(
            tmp_path,
            locale,
            name=name,
            native_name=native_name,
        )
        _write_fragment(
            tmp_path,
            locale,
            "dashboard",
            {"dashboard.title": title},
        )

    catalogs = CatalogSet.load(tmp_path, base_locale="ru-RU")

    assert catalogs.available_locales() == ("en-US", "es-ES", "ru-RU")
    assert catalogs.catalog("es-ES").text("dashboard.title") == "Panel de control"


def test_catalog_fragment_rejects_duplicate_root_key(tmp_path: Path) -> None:
    _write_root(tmp_path, "ru-RU", name="Russian", native_name="Русский")
    _write_root(tmp_path, "en-US", name="English", native_name="English")
    _write_fragment(
        tmp_path,
        "ru-RU",
        "dashboard",
        {"base.message": "дубликат"},
    )
    _write_fragment(
        tmp_path,
        "en-US",
        "dashboard",
        {"base.message": "duplicate"},
    )

    with pytest.raises(CatalogValidationError, match="duplicates message keys"):
        CatalogSet.load(tmp_path, base_locale="ru-RU")
