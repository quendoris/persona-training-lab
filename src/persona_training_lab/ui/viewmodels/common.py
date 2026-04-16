from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NavigationItem:
    key: str
    title: str
