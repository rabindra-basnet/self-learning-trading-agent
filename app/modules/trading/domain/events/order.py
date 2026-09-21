from __future__ import annotations

from dataclasses import dataclass

from app.core.messaging.bus import DomainEvent
from app.modules.trading.domain.value_objects.order import OrderStatus


@dataclass(frozen=True, slots=True)
class OrderStateChanged(DomainEvent):
    order_id: str
    status: OrderStatus
    symbol: str
