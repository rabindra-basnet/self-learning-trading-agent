from __future__ import annotations

from app.core.common.result import Err, Ok, Result
from app.modules.trading.domain.entities import TradeOrder
from app.modules.trading.domain.events import OrderStateChanged
from app.modules.trading.domain.portfolio import Position
from app.modules.trading.domain.portfolio_ports import PositionRepository
from app.modules.trading.domain.ports import EventPublisher


class ApplyFillService:
    def __init__(
        self,
        positions: PositionRepository,
        publisher: EventPublisher,
    ) -> None:
        self._positions = positions
        self._publisher = publisher

    async def execute(self, order: TradeOrder) -> Result[Position, str]:
        if order.status.value != "filled" or order.executed_price is None:
            return Err("order_is_not_filled")

        position = await self._positions.get(order.symbol)
        if position is None:
            position = Position.empty(order.symbol)

        try:
            updated = position.apply_fill(
                side=order.side.value,
                quantity=order.quantity,
                price=order.executed_price,
            )
        except ValueError as exc:
            return Err(str(exc))

        await self._positions.save(updated)
        await self._publisher.publish(
            OrderStateChanged(
                order_id=str(order.id),
                status=order.status,
                symbol=order.symbol,
            )
        )
        return Ok(updated)
