"""Infrastructure adapter exposing the strategy slice to backtests."""

from __future__ import annotations

from app.modules.strategies.application.manager import StrategyManager


class StrategyManagerGateway:
    def __init__(self, manager: StrategyManager) -> None:
        self._manager = manager

    async def get_strategy(self, strategy_id: str):
        return await self._manager.get_strategy(strategy_id)

    async def evaluate(self, strategy_id: str, candles, features):
        return await self._manager.evaluate(strategy_id, candles, features)
