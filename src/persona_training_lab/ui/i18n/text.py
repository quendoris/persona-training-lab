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
    *,
    count: int | None = None,
    **values: object,
) -> str:
    if localization is not None:
        return localization.text(key, count=count, **values)
    return base_catalog().text(
        key,
        count=count,
        values=values,
    )


def render_user_message(
    localization: LocalizationManager | None,
    message: UserMessage | str,
) -> str:
    """Render semantic messages at the UI boundary; strings are transitional."""

    if isinstance(message, UserMessage):
        return text(
            localization,
            message.key,
            **dict(message.values),
        )
    return message
