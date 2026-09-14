"""Time source port + implementations (pure, no framework)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def utcnow(self) -> datetime: ...


class SystemClock:
    def utcnow(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    """Deterministic clock for backtests, seeding, and tests."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def utcnow(self) -> datetime:
        return self._now
