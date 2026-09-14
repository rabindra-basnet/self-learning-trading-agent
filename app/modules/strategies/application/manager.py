"""strategies application service — pure orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from app.core.common.result import Err, Ok, Result
from app.core.exceptions.taxonomy import DomainError, NotFoundError
from app.core.messaging.bus import EventBus
from app.modules.marketdata.contracts import Candle
from app.modules.signals.contracts import FeatureVector
from app.modules.strategies.domain.entities import StrategyMeta, StrategyRegistered
from app.modules.strategies.domain.ports import Strategy


class StrategyStore(Protocol):
    def register(self, strategy: Strategy) -> None: ...

    def get(self, strategy_id: str) -> Strategy | None: ...

    def list_meta(self) -> list[StrategyMeta]: ...


class StrategyManager:
    def __init__(self, store: StrategyStore, bus: EventBus) -> None:
        self._store = store
        self._bus = bus

    async def register(self, strategy: Strategy) -> None:
        self._store.register(strategy)
        await self._bus.publish(StrategyRegistered(strategy_id=strategy.strategy_id, name=strategy.params.name))

    def list(self) -> list[StrategyMeta]:
        return self._store.list_meta()

    def get_strategy(self, strategy_id: str):
        return self._store.get(strategy_id)

    def evaluate(
        self, strategy_id: str, candles: Sequence[Candle], features: Sequence[FeatureVector]
    ) -> Result[str, DomainError]:
        strategy = self._store.get(strategy_id)
        if strategy is None:
            return Err(NotFoundError(f"unknown strategy: {strategy_id}"))
        return Ok(strategy.evaluate(candles, features).value)
