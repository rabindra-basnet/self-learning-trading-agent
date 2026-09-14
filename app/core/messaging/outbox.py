"""Transactional outbox: reliable event emission.

Events are recorded atomically with the producing transaction, then an
`OutboxPublisher` dispatches them to the bus (at-least-once, idempotent consumers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.core.common.clock import Clock, SystemClock
from app.core.logging.setup import get_logger
from app.core.messaging.bus import DomainEvent, EventBus
from app.core.observability.metrics import Meter

logger = get_logger("core.outbox")


class Outbox(Protocol):
    async def append(self, event: DomainEvent) -> None: ...

    async def mark_dispatched(self, event_id: str) -> None: ...

    async def next_undispatched(self, limit: int = 100) -> list[DomainEvent]: ...


@dataclass(slots=True)
class NoopOutbox:
    """Non-durable outbox — events are published directly to the bus."""

    async def append(self, event: DomainEvent) -> None:
        return None

    async def mark_dispatched(self, event_id: str) -> None:
        return None

    async def next_undispatched(self, limit: int = 100) -> list[DomainEvent]:
        return []


@dataclass(slots=True)
class InMemoryOutbox:
    events: dict[str, DomainEvent] = field(default_factory=dict)
    _dispatched: set[str] = field(default_factory=set)
    clock: Clock = field(default_factory=SystemClock)

    async def append(self, event: DomainEvent) -> None:
        self.events[event.event_id] = event

    async def mark_dispatched(self, event_id: str) -> None:
        self._dispatched.add(event_id)

    async def next_undispatched(self, limit: int = 100) -> list[DomainEvent]:
        pending = [e for eid, e in self.events.items() if eid not in self._dispatched]
        return pending[:limit]


@dataclass(slots=True)
class OutboxPublisher:
    """Poll-and-deliver runner for the outbox."""

    outbox: Outbox
    bus: EventBus
    meter: Meter
    batch_size: int = 100

    async def dispatch_pending(self, limit: int | None = None) -> int:
        pending = await self.outbox.next_undispatched(limit or self.batch_size)
        delivered = 0
        for event in pending:
            try:
                await self.bus.publish(event)
                await self.outbox.mark_dispatched(event.event_id)
                delivered += 1
            except Exception as exc:  # bus failures are retryable by design
                logger.warning("outbox_dispatch_failed", event=event.type_name, error=repr(exc))
        if delivered:
            self.meter.counter("outbox_dispatched", delivered)
        return delivered
