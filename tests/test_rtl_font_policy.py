from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from persona_training_lab.ui.i18n import font_policy


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_rtl_ui_font_priority_prefers_ui_family_then_proportional_fallback() -> None:
    assert font_policy.choose_rtl_ui_font_family(
        ["FreeMono", "FreeSerif", "Noto Sans Arabic UI"]
    ) == "Noto Sans Arabic UI"
    assert font_policy.choose_rtl_ui_font_family(
        ["FreeMono", "FreeSerif"]
    ) == "FreeSerif"
    assert font_policy.choose_rtl_ui_font_family(["FreeMono"]) is None


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
