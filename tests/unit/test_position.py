from decimal import Decimal

from app.modules.trading.domain.portfolio import Position


def test_buy_then_partial_sell_tracks_realized_pnl():
    position = Position.empty("BTC/USDT")

    position = position.apply_fill(
        side="buy",
        quantity=Decimal("2"),
        price=Decimal("100"),
    )
    position = position.apply_fill(
        side="sell",
        quantity=Decimal("1"),
        price=Decimal("120"),
    )

    assert position.quantity == Decimal("1")
    assert position.average_entry_price == Decimal("100")
    assert position.realized_pnl == Decimal("20")
