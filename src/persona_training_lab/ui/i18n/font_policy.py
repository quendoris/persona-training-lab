from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication


RTL_UI_FONT_PREFERENCES: tuple[str, ...] = (
    "Noto Sans Arabic UI",
    "Noto Sans Arabic",
    "Noto Naskh Arabic UI",
    "Noto Naskh Arabic",
    "FreeSerif",
)
BUNDLED_RTL_UI_FONT_FILENAMES: tuple[str, ...] = (
    "NotoSansArabicUI-Regular.ttf",
    "NotoSansArabicUI-Bold.ttf",
)
_BASE_FAMILIES_PROPERTY = "ptl_base_font_families"
_RTL_FAMILY_PROPERTY = "ptl_rtl_ui_font_family"
_FONTS_ROOT = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def bundled_rtl_ui_font_paths() -> tuple[Path, ...]:
    return tuple(_FONTS_ROOT / filename for filename in BUNDLED_RTL_UI_FONT_FILENAMES)


@lru_cache(maxsize=1)
def register_bundled_rtl_ui_fonts() -> tuple[str, ...]:
    """Register packaged Arabic UI fonts and return their Qt family names."""

    families: list[str] = []
    for path in bundled_rtl_ui_font_paths():
        if not path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            continue
        for family in QFontDatabase.applicationFontFamilies(font_id):
            if family not in families:
                families.append(family)
    return tuple(families)


def choose_rtl_ui_font_family(available_families: Iterable[str]) -> str | None:
    available = set(available_families)
    for family in RTL_UI_FONT_PREFERENCES:
        if family in available:
            return family
    return None


def rtl_ui_font_family() -> str | None:
    bundled = register_bundled_rtl_ui_fonts()
    system_arabic = QFontDatabase.families(QFontDatabase.WritingSystem.Arabic)
    return choose_rtl_ui_font_family((*bundled, *system_arabic))


def apply_locale_font_policy(app: QApplication, *, direction: str) -> str | None:
    """Use a packaged Arabic UI family without changing UI geometry.

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
