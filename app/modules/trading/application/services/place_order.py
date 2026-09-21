from __future__ import annotations

from app.core.common.clock import Clock
from app.core.common.result import Err, Ok, Result
from app.modules.trading.application.commands.place_order import PlaceOrderCommand
from app.modules.trading.domain.entities import OrderStateChanged, TradeOrder


class PlaceOrderService:
    def __init__(self, repository, gateway, risk_gate, clock: Clock, publisher) -> None:
        self._repository = repository
        self._gateway = gateway
        self._risk_gate = risk_gate
        self._clock = clock
        self._publisher = publisher

    async def execute(self, command: PlaceOrderCommand) -> Result[TradeOrder, str]:
        existing = await self._repository.get_by_client_order_id(command.client_order_id)
        if existing is not None:
            return Ok(existing)

        notional = command.quantity * command.price
        allowed, reason = await self._risk_gate.authorize(
            symbol=command.symbol,
            notional=notional,
            equity=command.equity,
        )
        if not allowed:
            return Err(f"risk_rejected:{reason}")

        try:
            order = TradeOrder.create(
                symbol=command.symbol,
                side=command.side,
                quantity=command.quantity,
                requested_price=command.price,
                client_order_id=command.client_order_id,
                now=self._clock.utcnow(),
            )
            submitted = await self._gateway.submit_market_order(order)
        except ValueError as exc:
            return Err(str(exc))

        await self._repository.save(submitted)
        await self._publisher.publish(
            OrderStateChanged(
                order_id=str(submitted.id),
                status=submitted.status,
                symbol=submitted.symbol,
            )
        )
        return Ok(submitted)
