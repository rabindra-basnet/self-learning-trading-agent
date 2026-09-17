"""strategy manager: register, list, evaluate."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.common.result import Err, Ok, Result
from app.core.exceptions.taxonomy import DomainError, NotFoundError
from app.core.messaging.bus import EventBus
from app.modules.strategies.domain.entities import StrategyMeta, StrategyRegistered
from app.modules.strategies.domain.ports import SignalDirection, Strategy, StrategyStore


class StrategyManager:
    """Owns the strategy catalog behind a store port."""

    def __init__(self, store: StrategyStore, bus: EventBus) -> None:
        self._store = store
        self._bus = bus

    async def register(self, strategy: Strategy) -> None:
        await self._store.put(strategy)
        await self._bus.publish(StrategyRegistered(strategy_id=strategy.strategy_id, name=strategy.params.name))

    async def get_strategy(self, strategy_id: str) -> Strategy | None:
        return await self._store.get(strategy_id)

    async def list(self) -> list[StrategyMeta]:
        return [StrategyMeta(strategy_id=s.strategy_id, name=s.params.name, params={}) for s in await self._store.all()]

    async def evaluate(
        self, strategy_id: str, candles: Sequence[Any], features: Sequence[Any]
    ) -> Result[SignalDirection, DomainError]:
        strategy = await self._store.get(strategy_id)
        if strategy is None:
            return Err(NotFoundError(f"unknown strategy: {strategy_id}"))
        return Ok(strategy.evaluate(candles, features))
