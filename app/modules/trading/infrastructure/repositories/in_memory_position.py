from __future__ import annotations

from app.modules.trading.domain.portfolio import Position


class InMemoryPositionRepository:
    def __init__(self) -> None:
        self._positions: dict[str, Position] = {}

    async def get(self, symbol: str) -> Position | None:
        return self._positions.get(symbol.upper())

    async def save(self, position: Position) -> None:
        self._positions[position.symbol.upper()] = position
