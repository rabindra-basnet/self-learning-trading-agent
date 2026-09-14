"""Redis Streams EventBus — durable, multi-process capable adapter.

Publishes events to a Redis Stream *and* delivers to in-process subscribers,
so both local handlers and external consumer-group workers receive them.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncGenerator

from app.core.logging.setup import get_logger
from app.core.messaging.bus import DomainEvent, EventHandler
from redis.asyncio import Redis

logger = get_logger("capability.bus.redis")


class RedisEventBus:
    def __init__(self, redis: Redis, stream: str = "domain_events") -> None:
        self._redis = redis
        self._stream = stream
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = {}

    async def publish(self, *events: DomainEvent) -> None:
        for event in events:
            payload = event.model_dump(mode="json")
            await self._redis.xadd(self._stream, {"payload": json.dumps(payload)})
            for handler in self._handlers.get(type(event), []):
                try:
                    await handler(event)
                except Exception as exc:
                    logger.warning("handler_failure", event=event.type_name, error=repr(exc))

    async def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def create_consumer_group(self, group: str) -> None:
        with contextlib.suppress(Exception):
            await self._redis.xgroup_create(self._stream, group, id="0", mkstream=True)

    async def consume_stream(
        self, group: str, consumer: str, batch: int = 100, block_ms: int = 5000
    ) -> AsyncGenerator[DomainEvent, None]:
        while True:
            try:
                entries = await self._redis.xreadgroup(
                    group, consumer, {self._stream: ">"}, count=batch, block=block_ms
                )
                if not entries:
                    continue
                for _stream_name, messages in entries:
                    for msg_id, fields in messages:
                        try:
                            raw = fields.get("payload", "{}")
                            data = json.loads(raw)
                            event_type_name = data.get("type", "")
                            payload = data.get("data", {})
                            handler = self._handler_by_name(event_type_name)
                            if handler is not None:
                                event = handler(**payload)
                                yield event
                            await self._redis.xack(self._stream, group, msg_id)
                        except Exception as exc:
                            logger.warning("stream_message_failure", msg_id=msg_id, error=repr(exc))
                            await self._redis.xack(self._stream, group, msg_id)
            except Exception as exc:
                logger.warning("stream_read_failure", group=group, consumer=consumer, error=repr(exc))
                await asyncio.sleep(1.0)

    def _handler_by_name(self, event_type_name: str) -> type[DomainEvent] | None:

        for t in self._handlers:
            if t.__name__ == event_type_name:
                return t
        return None

    async def close(self) -> None:
        with contextlib.suppress(Exception):
            await self._redis.aclose()
