from __future__ import annotations

from typing import Protocol

from app.modules.trading.domain.portfolio import Position


class PositionRepository(Protocol):
    async def get(self, symbol: str) -> Position | None: ...
    async def save(self, position: Position) -> None: ...
