from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.modules.trading.domain.entities import TradeOrder


class CcxtOrderGateway:
    """CCXT adapter; exchange details never leak into the application layer."""

    def __init__(self, exchange: Any) -> None:
        self._exchange = exchange

    async def submit_market_order(self, order: TradeOrder) -> TradeOrder:
        try:
            result = await self._exchange.create_order(
                order.symbol,
                "market",
                order.side.value,
                float(order.quantity),
            )
        except Exception as exc:
            raise RuntimeError(f"exchange_order_failed:{type(exc).__name__}") from exc

        status = str(result.get("status") or "").lower()
        filled = Decimal(str(result.get("filled") or "0"))
        average = result.get("average") or result.get("price") or order.requested_price

        if status in {"closed", "filled"} or filled > 0:
            return order.fill(Decimal(str(average)))

        return order
