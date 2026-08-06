from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from types import MappingProxyType
from typing import Mapping, TypeAlias


MessageValue: TypeAlias = str | Mapping[str, str]
_REQUIRED_META_FIELDS = {
    "schema",
    "locale",
    "name",
    "native_name",
    "direction",
}


class CatalogValidationError(ValueError):
    """Raised when a locale catalog cannot guarantee complete translation."""


@dataclass(frozen=True, slots=True)
class LocaleMetadata:
    schema: int
    locale: str
    name: str
    native_name: str
    direction: str


@dataclass(frozen=True, slots=True)
class LocaleCatalog:
    metadata: LocaleMetadata
    messages: Mapping[str, MessageValue]

    @classmethod
    def load(cls, path: Path) -> LocaleCatalog:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise CatalogValidationError(
                f"Cannot read locale catalog {path}: {error}"
            ) from error
        except json.JSONDecodeError as error:
            raise CatalogValidationError(
                f"Invalid JSON in locale catalog {path}: {error}"
            ) from error

        if not isinstance(payload, dict):
            raise CatalogValidationError(
                f"Locale catalog {path} must contain a JSON object"
            )
        raw_meta = payload.get("meta")
        raw_messages = payload.get("messages")
        if not isinstance(raw_meta, dict):
            raise CatalogValidationError(
                f"Locale catalog {path} has no valid meta object"
            )
        missing_meta = sorted(_REQUIRED_META_FIELDS - raw_meta.keys())
        if missing_meta:
            raise CatalogValidationError(
                f"Locale catalog {path} is missing meta fields: "
                + ", ".join(missing_meta)
            )
        if not isinstance(raw_messages, dict):
            raise CatalogValidationError(
                f"Locale catalog {path} has no valid messages object"
            )

        metadata = LocaleMetadata(
            schema=int(raw_meta["schema"]),
            locale=str(raw_meta["locale"]),
            name=str(raw_meta["name"]),
            native_name=str(raw_meta["native_name"]),
            direction=str(raw_meta["direction"]).lower(),
        )
        if metadata.schema != 1:
            raise CatalogValidationError(
                f"Unsupported catalog schema {metadata.schema} in {path}"
            )
        if metadata.direction not in {"ltr", "rtl"}:
            raise CatalogValidationError(
                f"Invalid text direction {metadata.direction!r} in {path}"
            )
        if path.stem != metadata.locale:
            raise CatalogValidationError(
                f"Catalog filename {path.stem!r} does not match locale "
                f"{metadata.locale!r}"
            )

        messages: dict[str, MessageValue] = {}
        for key, value in raw_messages.items():
            normalized_key = str(key).strip()
            if not normalized_key or normalized_key != key:
                raise CatalogValidationError(
                    f"Invalid message key {key!r} in {path}"
                )
            messages[normalized_key] = _normalize_message_value(
                normalized_key,
                value,
                path,
            )

        if not messages:
            raise CatalogValidationError(
                f"Locale catalog {path} must contain at least one message"
            )
        return cls(metadata, MappingProxyType(messages))

    def text(
        self,
        key: str,
        *,
        count: int | None = None,
        values: Mapping[str, object] | None = None,
    ) -> str:
        try:
            message = self.messages[key]
        except KeyError as error:
            raise CatalogValidationError(
                f"Missing translation key {key!r} in {self.metadata.locale}"
            ) from error

        template: str
        if isinstance(message, str):
            template = message
        else:
            if count is None:
                raise CatalogValidationError(
                    f"Plural message {key!r} requires count"
                )
            category = _plural_category(self.metadata.locale, count)
            template = message.get(category) or message["other"]

        format_values = dict(values or {})
        if count is not None:
            format_values.setdefault("count", count)
        required = _placeholder_names(template)
        missing = sorted(required - format_values.keys())
        if missing:
            raise CatalogValidationError(
                f"Message {key!r} in {self.metadata.locale} is missing values: "
                + ", ".join(missing)
            )
        try:
            return template.format_map(format_values)
        except (KeyError, ValueError) as error:
            raise CatalogValidationError(
                f"Cannot format message {key!r} in {self.metadata.locale}: "
                f"{error}"
            ) from error


@dataclass(frozen=True, slots=True)
class CatalogSet:
    base_locale: str
    catalogs: Mapping[str, LocaleCatalog]

    @classmethod
    def load(cls, directory: Path, *, base_locale: str) -> CatalogSet:
        paths = sorted(directory.glob("*.json"))
        if not paths:
            raise CatalogValidationError(
                f"No locale catalogs found in {directory}"
            )
        catalogs: dict[str, LocaleCatalog] = {}
        for path in paths:
            catalog = LocaleCatalog.load(path)
            locale = catalog.metadata.locale
            if locale in catalogs:
                raise CatalogValidationError(
                    f"Duplicate locale catalog {locale!r}"
                )
            catalogs[locale] = catalog
        if base_locale not in catalogs:
            raise CatalogValidationError(
                f"Base locale {base_locale!r} is not available"
            )
        result = cls(base_locale, MappingProxyType(catalogs))
        result.validate_complete()
        return result

    def validate_complete(self) -> None:
        base = self.catalogs[self.base_locale]
        base_keys = set(base.messages)
        for locale, catalog in self.catalogs.items():
            keys = set(catalog.messages)
            missing = sorted(base_keys - keys)
            extra = sorted(keys - base_keys)
            if missing or extra:
                fragments: list[str] = []
                if missing:
                    fragments.append("missing: " + ", ".join(missing))
                if extra:
                    fragments.append("extra: " + ", ".join(extra))
                raise CatalogValidationError(
                    f"Catalog {locale} does not match {self.base_locale}: "
                    + "; ".join(fragments)
                )

            for key in sorted(base_keys):
                base_signature = _message_signature(base.messages[key])
                locale_signature = _message_signature(catalog.messages[key])
                if base_signature != locale_signature:
                    raise CatalogValidationError(
                        f"Placeholder mismatch for {key!r}: "
                        f"{self.base_locale}={sorted(base_signature)}, "
                        f"{locale}={sorted(locale_signature)}"
                    )

    def catalog(self, locale: str) -> LocaleCatalog:
        try:
            return self.catalogs[locale]
        except KeyError as error:
            raise CatalogValidationError(
                f"Unsupported locale {locale!r}"
            ) from error

    def available_locales(self) -> tuple[str, ...]:
        return tuple(sorted(self.catalogs))


def _normalize_message_value(
    key: str,
    value: object,
    path: Path,
) -> MessageValue:
    if isinstance(value, str):
        if not value.strip():
            raise CatalogValidationError(
                f"Message {key!r} is empty in {path}"
            )
        _validate_template(key, value, path)
        return value
    if not isinstance(value, dict):
        raise CatalogValidationError(
            f"Message {key!r} in {path} must be a string or plural object"
        )
    normalized: dict[str, str] = {}
    for category, template in value.items():
        if category not in {"zero", "one", "two", "few", "many", "other"}:
            raise CatalogValidationError(
                f"Message {key!r} in {path} has invalid plural category "
                f"{category!r}"
            )
        if not isinstance(template, str) or not template.strip():
            raise CatalogValidationError(
                f"Message {key!r}/{category} is empty in {path}"
            )
        _validate_template(key, template, path)
        normalized[category] = template
    if "other" not in normalized:
        raise CatalogValidationError(
            f"Plural message {key!r} in {path} requires an 'other' form"
        )
    return MappingProxyType(normalized)


def _validate_template(key: str, template: str, path: Path) -> None:
    try:
        tuple(Formatter().parse(template))
    except ValueError as error:
        raise CatalogValidationError(
            f"Invalid format string for {key!r} in {path}: {error}"
        ) from error


def _message_signature(value: MessageValue) -> frozenset[str]:
    if isinstance(value, str):
        return frozenset(_placeholder_names(value))
    placeholders: set[str] = set()
    for template in value.values():
        placeholders.update(_placeholder_names(template))
    return frozenset(placeholders)


def _placeholder_names(template: str) -> set[str]:
    names: set[str] = set()
    for _literal, field_name, _format_spec, _conversion in Formatter().parse(
        template
    ):
        if field_name:
            names.add(field_name.split(".", 1)[0].split("[", 1)[0])
    return names


def _plural_category(locale: str, count: int) -> str:
    language = locale.split("-", 1)[0].lower()
    absolute = abs(count)
    if language == "ru":
        mod10 = absolute % 10
        mod100 = absolute % 100
        if mod10 == 1 and mod100 != 11:
            return "one"
        if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
            return "few"
        return "many"
    if language == "en":
        return "one" if absolute == 1 else "other"
    return "other"
