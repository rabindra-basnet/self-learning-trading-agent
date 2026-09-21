from __future__ import annotations

from decimal import Decimal

from app.modules.trading.domain.entities import TradeOrder


class PaperOrderGateway:
    async def submit_market_order(self, order: TradeOrder) -> TradeOrder:
        # Deterministic paper execution: no exchange/network dependency.
        executed_price = order.requested_price.quantize(Decimal("0.00000001"))
        return order.fill(executed_price)
