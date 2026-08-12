from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from persona_training_lab.application.messages import UserMessage
from persona_training_lab.i18n.catalog import CatalogSet, LocaleCatalog
from persona_training_lab.ui.i18n.manager import LocalizationManager


@lru_cache(maxsize=1)
def base_catalog() -> LocaleCatalog:
    directory = Path(
        str(files("persona_training_lab.i18n").joinpath("catalogs"))
    )
    return CatalogSet.load(
        directory,
        base_locale="ru-RU",
    ).catalog("ru-RU")


def text(
    localization: LocalizationManager | None,
    key: str,
    **values: object,
) -> str:
    if localization is not None:
        return localization.text(key, **values)
    format_values = dict(values)
    count = _extract_count(format_values)
    return base_catalog().text(
        key,
        count=count,
        values=format_values,
    )


def render_user_message(
    localization: LocalizationManager | None,
    message: UserMessage | str,
) -> str:
    """Render semantic messages at the UI boundary; strings are transitional."""

    if isinstance(message, UserMessage):
        values = {
            key: _render_message_value(localization, value)
            for key, value in message.values.items()
        }
        return text(
            localization,
            message.key,
            **values,
        )
    return message


def _render_message_value(
    localization: LocalizationManager | None,
    value: object,
) -> object:
    if isinstance(value, UserMessage):
        return render_user_message(localization, value)
    return value


def _extract_count(values: dict[str, object]) -> int | None:
    raw_count = values.pop("count", None)
    if raw_count is None:
        return None
    if type(raw_count) is not int:
        raise TypeError("localization count must be an integer or None")
    return raw_count
