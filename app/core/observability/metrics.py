"""Metrics capability port — implementations live in infrastructure."""

from __future__ import annotations

from typing import Protocol


class Meter(Protocol):
    def counter(self, name: str, value: int = 1, labels: dict[str, str] | None = None) -> None: ...

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None: ...
