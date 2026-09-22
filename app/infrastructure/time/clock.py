"""System clock infrastructure adapter."""

from __future__ import annotations

from datetime import UTC, datetime

from magic_di import Connectable


class SystemClock(Connectable):
    def utcnow(self) -> datetime:
        return datetime.now(UTC)
