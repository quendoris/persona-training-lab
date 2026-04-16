from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(slots=True, frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(slots=True, frozen=True)
class Err(Generic[E]):
    error: E
