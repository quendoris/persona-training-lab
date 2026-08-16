from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any
from weakref import ReferenceType, ref

from PySide6.QtCore import QLibraryInfo, QLocale, QObject, Qt, QTranslator, Signal
from PySide6.QtWidgets import QApplication, QWidget

from persona_training_lab.i18n.catalog import (
    CatalogSet,
    CatalogValidationError,
    LocaleCatalog,
)


ValuesProvider = Callable[[], Mapping[str, object]]
CountProvider = Callable[[], int | None]
PersistLocale = Callable[[str], None]


@dataclass(slots=True)
class _Binding:
    target: ReferenceType[QObject]
    setter_name: str
    key: str
    values_provider: ValuesProvider | None
    count_provider: CountProvider | None


class LocalizationManager(QObject):
    """Own application catalogs, Qt translations and live widget bindings."""

    language_changed = Signal(str)

    def __init__(
        self,
        app: QApplication,
        *,
        initial_locale: str = "ru-RU",
        catalog_directory: Path | None = None,
        persist_locale: PersistLocale | None = None,
    ) -> None:
        super().__init__(app)
        self._app = app
        self._catalog_directory = catalog_directory or Path(
            str(files("persona_training_lab.i18n").joinpath("catalogs"))
        )
        self._catalogs = CatalogSet.load(
            self._catalog_directory,
            base_locale="ru-RU",
        )
        self._catalog: LocaleCatalog = self._catalogs.catalog("ru-RU")
        self._locale = "ru-RU"
        self._persist_locale = persist_locale
        self._qt_translator: QTranslator | None = None
        self._bindings: list[_Binding] = []
        self.set_locale(initial_locale, persist=False)

    @property
    def locale(self) -> str:
        return self._locale

    @property
    def catalog_set(self) -> CatalogSet:
        return self._catalogs

    def available_locales(self) -> tuple[str, ...]:
        return self._catalogs.available_locales()

    def locale_name(self, locale: str) -> str:
        return self._catalogs.catalog(locale).metadata.native_name

    def text(self, key: str, **values: object) -> str:
        format_values = dict(values)
        count = _extract_count(format_values)
        return self._catalog.text(
            key,
            count=count,
            values=format_values,
        )

    def set_locale(self, locale: str, *, persist: bool = True) -> None:
        target_catalog = self._catalogs.catalog(locale)
        rendered = self._render_bindings(target_catalog)
        target_qt_translator = self._prepare_qt_translator(locale)

        previous_translator = self._qt_translator
        if previous_translator is not None:
            self._app.removeTranslator(previous_translator)
        if target_qt_translator is not None:
            self._app.installTranslator(target_qt_translator)

        self._catalog = target_catalog
        self._locale = locale
        self._qt_translator = target_qt_translator
        layout_direction = (
            Qt.LayoutDirection.RightToLeft
            if target_catalog.metadata.direction == "rtl"
            else Qt.LayoutDirection.LeftToRight
        )
        self._app.setLayoutDirection(layout_direction)
        QLocale.setDefault(QLocale(locale.replace("-", "_")))
        self._app.setProperty("ptl_locale", locale)

        self._apply_rendered_bindings(rendered)
        self.language_changed.emit(locale)
        if persist and self._persist_locale is not None:
            self._persist_locale(locale)

    def bind_text(
        self,
        target: QObject,
        key: str,
        *,
        values_provider: ValuesProvider | None = None,
        count_provider: CountProvider | None = None,
    ) -> None:
        self._bind(
            target,
            "setText",
            key,
            values_provider=values_provider,
            count_provider=count_provider,
        )

    def bind_title(
        self,
        target: QObject,
        key: str,
        *,
        values_provider: ValuesProvider | None = None,
        count_provider: CountProvider | None = None,
    ) -> None:
        """Bind objects such as QMenu that expose setTitle()."""

        self._bind(
            target,
            "setTitle",
            key,
            values_provider=values_provider,
            count_provider=count_provider,
        )

    def bind_tooltip(
        self,
        target: QObject,
        key: str,
        *,
        values_provider: ValuesProvider | None = None,
        count_provider: CountProvider | None = None,
    ) -> None:
        self._bind(
            target,
            "setToolTip",
            key,
            values_provider=values_provider,
            count_provider=count_provider,
        )

    def bind_window_title(
        self,
        target: QWidget,
        key: str,
        *,
        values_provider: ValuesProvider | None = None,
    ) -> None:
        self._bind(
            target,
            "setWindowTitle",
            key,
            values_provider=values_provider,
        )

    def bind_placeholder(
        self,
        target: QObject,
        key: str,
        *,
        values_provider: ValuesProvider | None = None,
    ) -> None:
        self._bind(
            target,
            "setPlaceholderText",
            key,
            values_provider=values_provider,
        )

    def refresh(self) -> None:
        rendered = self._render_bindings(self._catalog)
        self._apply_rendered_bindings(rendered)

    def _bind(
        self,
        target: QObject,
        setter_name: str,
        key: str,
        *,
        values_provider: ValuesProvider | None = None,
        count_provider: CountProvider | None = None,
    ) -> None:
        setter = getattr(target, setter_name, None)
        if not callable(setter):
            raise TypeError(
                f"{type(target).__name__} does not provide {setter_name}()"
            )
        binding = _Binding(
            target=ref(target),
            setter_name=setter_name,
            key=key,
            values_provider=values_provider,
            count_provider=count_provider,
        )
        value = self._render_binding(binding, self._catalog)
        setter(value)
        self._bindings.append(binding)
        target.destroyed.connect(self._prune_bindings)

    def _render_bindings(
        self,
        catalog: LocaleCatalog,
    ) -> list[tuple[_Binding, str]]:
        rendered: list[tuple[_Binding, str]] = []
        for binding in self._bindings:
            if binding.target() is None:
                continue
            rendered.append((binding, self._render_binding(binding, catalog)))
        return rendered

    @staticmethod
    def _render_binding(
        binding: _Binding,
        catalog: LocaleCatalog,
    ) -> str:
        values = (
            dict(binding.values_provider())
            if binding.values_provider is not None
            else {}
        )
        count = (
            binding.count_provider()
            if binding.count_provider is not None
            else None
        )
        return catalog.text(binding.key, count=count, values=values)

    def _apply_rendered_bindings(
        self,
        rendered: list[tuple[_Binding, str]],
    ) -> None:
        alive: list[_Binding] = []
        rendered_by_id = {id(binding): value for binding, value in rendered}
        for binding in self._bindings:
            target = binding.target()
            if target is None:
                continue
            setter = getattr(target, binding.setter_name, None)
            if not callable(setter):
                continue
            try:
                setter(rendered_by_id[id(binding)])
            except (KeyError, RuntimeError):
                continue
            alive.append(binding)
        self._bindings = alive

    def _prepare_qt_translator(self, locale: str) -> QTranslator | None:
        language = locale.split("-", 1)[0].lower()
        if language == "en":
            return None

        translations_path = Path(
            QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        )
        candidates = (
            translations_path / f"qtbase_{language}.qm",
            translations_path / f"qt_{language}.qm",
        )
        for candidate in candidates:
            if not candidate.is_file():
                continue
            translator = QTranslator(self)
            if translator.load(str(candidate)):
                return translator
        raise CatalogValidationError(
            f"Qt system translations for locale {locale!r} were not found in "
            f"{translations_path}"
        )

    def _prune_bindings(self, *_args: Any) -> None:
        self._bindings = [
            binding for binding in self._bindings if binding.target() is not None
        ]


def _extract_count(values: dict[str, object]) -> int | None:
    raw_count = values.pop("count", None)
    if raw_count is None:
        return None
    if type(raw_count) is not int:
        raise TypeError("localization count must be an integer or None")
    return raw_count
