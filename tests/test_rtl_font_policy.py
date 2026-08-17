from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.i18n import font_policy


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _git_blob_sha1(data: bytes) -> str:
    payload = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest()


def test_rtl_ui_font_priority_prefers_ui_family_then_proportional_fallback() -> None:
    assert font_policy.choose_rtl_ui_font_family(
        ["FreeMono", "FreeSerif", "Noto Sans Arabic UI"]
    ) == "Noto Sans Arabic UI"
    assert font_policy.choose_rtl_ui_font_family(
        ["FreeMono", "FreeSerif"]
    ) == "FreeSerif"
    assert font_policy.choose_rtl_ui_font_family(["FreeMono"]) is None


def test_bundled_noto_arabic_fonts_match_provenance_and_register(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    paths = font_policy.bundled_rtl_ui_font_paths()
    assets_root = paths[0].parent
    manifest = json.loads(
        (assets_root / "noto_arabic_ui.json").read_text(encoding="utf-8")
    )

    assert manifest["schema"] == 1
    assert manifest["family"] == "Noto Sans Arabic UI"
    assert manifest["upstream"] == {
        "repository": "notofonts/noto-fonts",
        "commit": "8ea3c95f7f8f6284c66a5c1d82b858cc187413a8",
    }

    license_spec = manifest["license"]
    license_path = assets_root / license_spec["filename"]
    assert license_path.is_file()
    assert _git_blob_sha1(license_path.read_bytes()) == license_spec["git_blob_sha1"]

    specs = {item["filename"]: item for item in manifest["fonts"]}
    assert set(specs) == {path.name for path in paths}
    for path in paths:
        assert path.is_file()
        data = path.read_bytes()
        spec = specs[path.name]
        assert len(data) == spec["size"]
        assert _git_blob_sha1(data) == spec["git_blob_sha1"]

    monkeypatch.chdir(tmp_path)
    font_policy.register_bundled_rtl_ui_fonts.cache_clear()
    families = font_policy.register_bundled_rtl_ui_fonts()
    assert "Noto Sans Arabic UI" in families
    assert font_policy.rtl_ui_font_family() == "Noto Sans Arabic UI"
    assert app is QApplication.instance()


def test_locale_font_policy_restores_family_without_rolling_back_scale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app()
    original = QFont(app.font())
    base = QFont(original)
    base.setFamilies(["Sans Serif"])
    base.setPointSizeF(9.5)
    app.setFont(base)

    monkeypatch.setattr(
        font_policy,
        "rtl_ui_font_family",
        lambda: "PTL Arabic UI Test",
    )

    try:
        selected = font_policy.apply_locale_font_policy(app, direction="rtl")
        assert selected == "PTL Arabic UI Test"
        assert app.font().families()[0] == "PTL Arabic UI Test"
        assert app.property("ptl_rtl_ui_font_family") == "PTL Arabic UI Test"

        scaled = QFont(app.font())
        scaled.setPointSizeF(10.5)
        app.setFont(scaled)

        assert font_policy.apply_locale_font_policy(app, direction="ltr") is None
        assert app.font().families() == ["Sans Serif"]
        assert app.font().pointSizeF() == pytest.approx(10.5)
        assert app.property("ptl_rtl_ui_font_family") is None
    finally:
        app.setFont(original)
        app.setProperty("ptl_base_font_families", None)
        app.setProperty("ptl_rtl_ui_font_family", None)
