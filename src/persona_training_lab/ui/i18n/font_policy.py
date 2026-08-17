from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


RTL_UI_FONT_PREFERENCES: tuple[str, ...] = (
    "Noto Sans Arabic UI",
    "Noto Sans Arabic",
    "Noto Naskh Arabic UI",
    "Noto Naskh Arabic",
    "FreeSerif",
)
_BASE_FAMILIES_PROPERTY = "ptl_base_font_families"
_RTL_FAMILY_PROPERTY = "ptl_rtl_ui_font_family"


def choose_rtl_ui_font_family(available_families: Iterable[str]) -> str | None:
    available = set(available_families)
    for family in RTL_UI_FONT_PREFERENCES:
        if family in available:
            return family
    return None


def rtl_ui_font_family() -> str | None:
    return choose_rtl_ui_font_family(
        QFontDatabase.families(QFontDatabase.WritingSystem.Arabic)
    )


def apply_locale_font_policy(app: QApplication, *, direction: str) -> str | None:
    """Use a proportional Arabic UI family without changing UI geometry.

    The original family stack is remembered independently from point size so
    density changes made while an RTL locale is active are preserved when the
    application later returns to an LTR locale.
    """

    current = QFont(app.font())
    stored_families = app.property(_BASE_FAMILIES_PROPERTY)

    if direction != "rtl":
        if isinstance(stored_families, list) and stored_families:
            current.setFamilies([str(family) for family in stored_families])
            app.setFont(current)
        app.setProperty(_BASE_FAMILIES_PROPERTY, None)
        app.setProperty(_RTL_FAMILY_PROPERTY, None)
        return None

    family = rtl_ui_font_family()
    if family is None:
        app.setProperty(_RTL_FAMILY_PROPERTY, None)
        return None

    if not isinstance(stored_families, list) or not stored_families:
        stored_families = list(current.families())
        if not stored_families:
            stored_families = [current.family()]
        app.setProperty(_BASE_FAMILIES_PROPERTY, stored_families)

    fallback = [
        str(candidate)
        for candidate in stored_families
        if str(candidate) and str(candidate) != family
    ]
    current.setFamilies([family, *fallback])
    app.setFont(current)
    app.setProperty(_RTL_FAMILY_PROPERTY, family)
    return family
