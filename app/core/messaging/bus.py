"""Domain event bus: capability port (EventBus) + in-process implementation.

Third-party buses (Redis Streams, Kafka/Redpanda) are adapters in
`app/infrastructure/capability/*` implementing this same port — slices never see them.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel

EventHandler = Callable[["DomainEvent"], Awaitable[None]]


class DomainEvent(BaseModel):
    """Base class for all domain events (carry normalized domain models)."""

    event_id: str = ""
    occurred_at: datetime | None = None

    def model_post_init(self, __context: Any) -> None:
        if not self.event_id:
            self.event_id = str(uuid4())
        if self.occurred_at is None:
            self.occurred_at = datetime.now(UTC)

    @property
    def type_name(self) -> str:
        return type(self).__name__


class EventBus(Protocol):
    async def publish(self, *events: DomainEvent) -> None: ...

    async def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None: ...


class InMemoryEventBus:
    """In-process async bus used in dev and tests."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}
        self.published: list[DomainEvent] = []

    async def publish(self, *events: DomainEvent) -> None:
        self.published.extend(events)
        for event in events:
            for handler in self._handlers.get(type(event), []):
                await handler(event)

    async def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)
