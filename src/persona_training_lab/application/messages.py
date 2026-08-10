from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class UserMessage:
    """Locale-independent reference to text that may be shown to a user."""

    key: str
    values: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        key = self.key.strip()
        if not key:
            raise ValueError("UserMessage key must not be empty")
        object.__setattr__(self, "key", key)
        object.__setattr__(
            self,
            "values",
            MappingProxyType(dict(self.values)),
        )


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Locale-neutral outcome for an application operation.

    ``code`` is a stable machine contract for GUI, CLI, recipes, tests, and
    automation. Human-readable text is selected only by a presentation
    boundary. ``values`` carries structured interpolation/provenance data and
    must never be parsed back out of rendered text.
    """

    ok: bool
    code: str
    values: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        code = self.code.strip()
        if not code:
            raise ValueError("ActionResult code must not be empty")
        object.__setattr__(self, "code", code)
        object.__setattr__(
            self,
            "values",
            MappingProxyType(dict(self.values)),
        )
