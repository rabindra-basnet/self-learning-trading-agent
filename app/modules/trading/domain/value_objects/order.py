from __future__ import annotations

from enum import StrEnum


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"


class OrderStatus(StrEnum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
