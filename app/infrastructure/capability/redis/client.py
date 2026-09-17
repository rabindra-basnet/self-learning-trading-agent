"""Redis async client — lifecycle wrapper (create, ping, dispose)."""

from __future__ import annotations

from app.core.config.settings import Settings
from app.core.logging.setup import get_logger
from magic_di import Connectable
from redis.asyncio import Redis, from_url

logger = get_logger("capability.redis")


class RedisConnection(Connectable):
    def __init__(self, settings: Settings) -> None:
        self._url = settings.redis_url
        self._client: Redis | None = None

    async def __disconnect__(self) -> None:
        await self.dispose()

    @property
    def client(self) -> Redis:
        if self._client is None:
            self._client = from_url(self._url, decode_responses=True)
        return self._client

    async def ping(self) -> bool:
        try:
            return bool(await self.client.ping())
        except Exception as exc:
            logger.warning("redis_ping_failed", error_type=type(exc).__name__, error=str(exc))
            return False

    async def dispose(self) -> None:
        if self._client is not None:
            await self.client.aclose()
            self._client = None
