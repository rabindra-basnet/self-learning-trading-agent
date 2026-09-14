"""Redis-backed transactional outbox — implements the Outbox port.

Append stores event JSON; mark_dispatched records delivery;
next_undispatched scans for undelivered ids (LRANGE + SISMEMBER filter).
"""

from __future__ import annotations

import json

from app.core.messaging.bus import DomainEvent
from redis.asyncio import Redis

_STREAM_PREFIX = "outbox:event:"
_PENDING_KEY = "outbox:pending"
_DONE_KEY = "outbox:dispatched"


class RedisOutbox:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def append(self, event: DomainEvent) -> None:
        key = f"{_STREAM_PREFIX}{event.event_id}"
        data = event.model_dump(mode="json")
        await self._redis.set(key, json.dumps(data))
        await self._redis.rpush(_PENDING_KEY, event.event_id)

    async def mark_dispatched(self, event_id: str) -> None:
        await self._redis.sadd(_DONE_KEY, event_id)

    async def next_undispatched(self, limit: int = 100) -> list[DomainEvent]:
        ids: list[str] = [
            eid.decode() if isinstance(eid, bytes) else eid for eid in (await self._redis.lrange(_PENDING_KEY, 0, -1))
        ]
        undispatched_ids: list[str] = []
        for eid in ids:
            if not await self._redis.sismember(_DONE_KEY, eid):
                undispatched_ids.append(eid)
            if len(undispatched_ids) >= limit:
                break
        events: list[DomainEvent] = []
        for eid in undispatched_ids:
            raw = await self._redis.get(f"{_STREAM_PREFIX}{eid}")
            if raw is None:
                continue
            try:
                data = json.loads(raw)
                type_name = data.get("type", "")
                payload = data.get("data", {})
                cls = self._resolve_type(type_name)
                if cls is not None:
                    events.append(cls(**payload))
            except Exception:
                pass
        return events

    def _resolve_type(self, type_name: str):
        from app.core.messaging.bus import DomainEvent as _DE

        for cls in _DE.__subclasses__():
            if cls.__name__ == type_name:
                return cls
        return None
