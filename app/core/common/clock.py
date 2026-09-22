"""Pure time-source port and deterministic test implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    def utcnow(self) -> datetime: ...


class FrozenClock:
    """Deterministic clock for backtests, seeding, and tests."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def utcnow(self) -> datetime:
        return self._now
