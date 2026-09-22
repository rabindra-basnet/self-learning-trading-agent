from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.trading.domain.entities import TradeOrder


class OrderRepository(Protocol):
    async def get(self, order_id: UUID) -> TradeOrder | None: ...

    async def get_by_client_order_id(self, client_order_id: str) -> TradeOrder | None: ...

    async def save(self, order: TradeOrder) -> None: ...
