from decimal import Decimal

import pytest

from app.modules.trading.domain.entities import OrderSide, TradeOrder
from app.modules.trading.infrastructure.gateways.ccxt_gateway import CcxtOrderGateway


class FakeExchange:
    async def create_order(self, symbol, order_type, side, quantity):
        assert symbol == "BTC/USDT"
        assert order_type == "market"
        assert side == "buy"
        assert quantity == 0.1
        return {"status": "closed", "filled": "0.1", "average": "101.25"}


@pytest.mark.asyncio
async def test_ccxt_gateway_maps_closed_order():
    from datetime import UTC, datetime

    order = TradeOrder.create(
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.1"),
        requested_price=Decimal("100"),
        client_order_id="ccxt-1",
        now=datetime.now(UTC),
    )

    result = await CcxtOrderGateway(FakeExchange()).submit_market_order(order)

    assert result.executed_price == Decimal("101.25")
    assert result.status.value == "filled"
