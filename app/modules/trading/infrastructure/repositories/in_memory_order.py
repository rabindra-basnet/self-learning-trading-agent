from __future__ import annotations

from uuid import UUID

from app.modules.trading.domain.entities import TradeOrder


class InMemoryOrderRepository:
    def __init__(self) -> None:
        self._orders: dict[UUID, TradeOrder] = {}
        self._client_ids: dict[str, UUID] = {}

    async def get(self, order_id: UUID) -> TradeOrder | None:
        return self._orders.get(order_id)

    async def get_by_client_order_id(self, client_order_id: str) -> TradeOrder | None:
        order_id = self._client_ids.get(client_order_id)
        return self._orders.get(order_id) if order_id else None

    async def save(self, order: TradeOrder) -> None:
        self._orders[order.id] = order
        self._client_ids[order.client_order_id] = order.id
