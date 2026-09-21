from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.trading.domain.entities import TradeOrder


class OrderRepository(Protocol):
    async def get(self, order_id: UUID) -> TradeOrder | None: ...
    async def get_by_client_order_id(self, client_order_id: str) -> TradeOrder | None: ...
    async def save(self, order: TradeOrder) -> None: ...


class OrderGateway(Protocol):
    async def submit_market_order(self, order: TradeOrder) -> TradeOrder: ...


class RiskGate(Protocol):
    async def authorize(
        self,
        *,
        symbol: str,
        notional: object,
        equity: object,
    ) -> tuple[bool, str]: ...


class EventPublisher(Protocol):
    async def publish(self, event: object) -> None: ...
