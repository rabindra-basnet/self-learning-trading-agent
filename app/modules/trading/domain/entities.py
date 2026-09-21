from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from app.core.messaging.bus import DomainEvent


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"


class OrderStatus(StrEnum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class TradeOrder:
    id: UUID
    symbol: str
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    status: OrderStatus
    requested_price: Decimal
    executed_price: Decimal | None
    client_order_id: str
    created_at: datetime
    rejection_reason: str | None = None

    @classmethod
    def create(
        cls,
        *,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        requested_price: Decimal,
        client_order_id: str,
        now: datetime,
    ) -> "TradeOrder":
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if requested_price <= 0:
            raise ValueError("requested_price must be positive")
        if not symbol.strip():
            raise ValueError("symbol must not be empty")
        if not client_order_id.strip():
            raise ValueError("client_order_id must not be empty")

        return cls(
            id=uuid4(),
            symbol=symbol.upper(),
            side=side,
            quantity=quantity,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
            requested_price=requested_price,
            executed_price=None,
            client_order_id=client_order_id,
            created_at=now,
        )

    def fill(self, executed_price: Decimal) -> "TradeOrder":
        if self.status is not OrderStatus.PENDING:
            raise ValueError("only pending orders can be filled")
        if executed_price <= 0:
            raise ValueError("executed_price must be positive")
        return replace(
            self,
            status=OrderStatus.FILLED,
            executed_price=executed_price,
        )

    def reject(self, reason: str) -> "TradeOrder":
        if self.status is not OrderStatus.PENDING:
            raise ValueError("only pending orders can be rejected")
        return replace(
            self,
            status=OrderStatus.REJECTED,
            rejection_reason=reason,
        )


class OrderStateChanged(DomainEvent):
    order_id: str
    status: OrderStatus
    symbol: str
