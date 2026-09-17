"""Redis RiskProfileStore adapter (Upstash / rediss compatible)."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, Protocol

from app.core.logging.setup import get_logger
from app.infrastructure.capability.redis import RedisConnection
from app.modules.risk.domain.entities import KillSwitchState, RiskProfile

logger = get_logger("stores.risk_redis")


class RedisClient(Protocol):
    def get(self, name: str) -> Awaitable[Any]: ...

    def set(self, name: str, value: str) -> Awaitable[Any]: ...


_PROFILE_KEY = "risk:profile"
_KILL_SWITCH_KEY = "risk:kill_switch"


class RedisRiskProfileStore:
    async def __connect__(self) -> None:
        pass

    async def __disconnect__(self) -> None:
        pass

    def __init__(self, redis: RedisConnection) -> None:
        self._client = redis.client

    async def get_profile(self) -> RiskProfile:
        raw = await self._client.get(_PROFILE_KEY)
        if raw is None:
            return RiskProfile()
        try:
            return RiskProfile.model_validate_json(raw)
        except Exception:
            logger.warning("risk_profile_corrupt", key=_PROFILE_KEY)
            return RiskProfile()

    async def save_profile(self, profile: RiskProfile) -> None:
        await self._client.set(_PROFILE_KEY, profile.model_dump_json())

    async def get_kill_switch(self) -> KillSwitchState:
        raw = await self._client.get(_KILL_SWITCH_KEY)
        if raw is None:
            return KillSwitchState()
        try:
            return KillSwitchState.model_validate_json(raw)
        except Exception:
            logger.warning("risk_kill_switch_corrupt", key=_KILL_SWITCH_KEY)
            return KillSwitchState()

    async def set_kill_switch(self, state: KillSwitchState) -> None:
        await self._client.set(_KILL_SWITCH_KEY, state.model_dump_json())
