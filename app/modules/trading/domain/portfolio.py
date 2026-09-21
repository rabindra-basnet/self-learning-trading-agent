from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    realized_pnl: Decimal = Decimal("0")

    @classmethod
    def empty(cls, symbol: str) -> "Position":
        return cls(symbol=symbol, quantity=Decimal("0"), average_entry_price=Decimal("0"))

    def apply_fill(
        self,
        *,
        side: str,
        quantity: Decimal,
        price: Decimal,
    ) -> "Position":
        if quantity <= 0 or price <= 0:
            raise ValueError("fill quantity and price must be positive")

        signed_quantity = quantity if side == "buy" else -quantity
        old_qty = self.quantity
        new_qty = old_qty + signed_quantity

        if old_qty == 0 or (old_qty > 0 and signed_quantity > 0) or (old_qty < 0 and signed_quantity < 0):
            total_cost = abs(old_qty) * self.average_entry_price + quantity * price
            return Position(
                symbol=self.symbol,
                quantity=new_qty,
                average_entry_price=total_cost / abs(new_qty),
                realized_pnl=self.realized_pnl,
            )

        closed = min(abs(old_qty), quantity)
        pnl_per_unit = price - self.average_entry_price
        if old_qty < 0:
            pnl_per_unit = -pnl_per_unit

        realized = closed * pnl_per_unit
        remaining = new_qty

        if remaining == 0:
            average = Decimal("0")
        elif (old_qty > 0 and remaining > 0) or (old_qty < 0 and remaining < 0):
            average = self.average_entry_price
        else:
            average = price

        return Position(
            symbol=self.symbol,
            quantity=remaining,
            average_entry_price=average,
            realized_pnl=self.realized_pnl + realized,
        )
