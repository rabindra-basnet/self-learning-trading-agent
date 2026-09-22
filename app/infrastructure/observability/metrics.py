"""No-op metrics infrastructure adapter."""

from __future__ import annotations

from magic_di import Connectable


class NoopMeter(Connectable):
    def counter(self, name: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
        return None

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        return None
