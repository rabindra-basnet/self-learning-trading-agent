from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.trading.domain.entities import TradeOrder
from app.modules.trading.domain.portfolio import Position
from app.modules.trading.domain.value_objects.order import OrderSide, OrderStatus


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=30)
    side: OrderSide
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    client_order_id: str = Field(min_length=1, max_length=100)
    equity: Decimal = Field(gt=0)


class OrderResponse(BaseModel):
    id: UUID
    symbol: str
    side: OrderSide
    quantity: Decimal
    status: OrderStatus
    requested_price: Decimal
    executed_price: Decimal | None
    client_order_id: str
    rejection_reason: str | None = None

    @classmethod
    def from_domain(cls, order: TradeOrder) -> OrderResponse:
        return cls(
            id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            status=order.status,
            requested_price=order.requested_price,
            executed_price=order.executed_price,
            client_order_id=order.client_order_id,
            rejection_reason=order.rejection_reason,
        )


class PositionResponse(BaseModel):
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    realized_pnl: Decimal

    @classmethod
    def from_domain(cls, position: Position) -> PositionResponse:
        return cls(
            symbol=position.symbol,
            quantity=position.quantity,
            average_entry_price=position.average_entry_price,
            realized_pnl=position.realized_pnl,
        )
