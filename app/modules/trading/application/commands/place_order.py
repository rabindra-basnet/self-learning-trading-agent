from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.trading.domain.entities import OrderSide


@dataclass(frozen=True, slots=True)
class PlaceOrderCommand:
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    client_order_id: str
    equity: Decimal
