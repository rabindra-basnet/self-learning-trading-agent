from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from app.modules.trading.application.commands.place_order import PlaceOrderCommand
from app.modules.trading.application.services.place_order import PlaceOrderService
from app.modules.trading.infrastructure.gateways.paper import PaperOrderGateway


class FixedClock:
    def utcnow(self):
        return datetime(2026, 1, 1, tzinfo=UTC)


class AllowRisk:
    async def authorize(self, **kwargs):
        return True, "ok"


class Events:
    def __init__(self):
        self.events = []

    async def publish(self, *events):
        self.events.extend(events)


@pytest.mark.asyncio
async def test_place_order_is_idempotent():
    repo = AsyncMock()
    events = Events()
    positions = AsyncMock()
    saved_order = None

    async def find_existing(client_order_id):
        return saved_order

    async def save(order):
        nonlocal saved_order
        saved_order = order

    repo.get_by_client_order_id.side_effect = find_existing
    repo.save.side_effect = save

    service = PlaceOrderService(repo, PaperOrderGateway(), AllowRisk(), FixedClock(), events, positions)
    command = PlaceOrderCommand(
        symbol="BTC/USDT",
        side="buy",
        quantity=Decimal("0.1"),
        price=Decimal("100"),
        client_order_id="demo-1",
        equity=Decimal("10000"),
    )

    first = await service.execute(command)
    second = await service.execute(command)

    assert first.is_ok
    assert second.is_ok
    assert first.ok_value().id == second.ok_value().id
    assert len(events.events) == 1
    repo.get_by_client_order_id.assert_awaited_twice()
    repo.save.assert_awaited_once()
