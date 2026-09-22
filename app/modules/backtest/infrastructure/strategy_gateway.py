"""Infrastructure adapter exposing the strategy slice to backtests."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.core.common.result import Result
from app.core.exceptions.taxonomy import DomainError
from app.modules.signals.contracts import FeatureVector
from app.modules.strategies.application.manager import StrategyManager
from app.modules.strategies.contracts import SignalDirection, Strategy


class StrategyManagerGateway:
    def __init__(self, manager: StrategyManager) -> None:
        self._manager = manager

    async def get_strategy(self, strategy_id: str) -> Strategy | None:
        return await self._manager.get_strategy(strategy_id)

    async def evaluate(
        self,
        strategy_id: str,
        candles: Sequence[Any],
        features: Sequence[FeatureVector],
    ) -> Result[SignalDirection, DomainError]:
        return await self._manager.evaluate(strategy_id, candles, features)
