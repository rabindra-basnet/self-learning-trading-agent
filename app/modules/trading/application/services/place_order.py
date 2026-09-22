from __future__ import annotations

from app.core.common.clock import Clock
from app.core.common.result import Err, Ok, Result
from app.modules.trading.application.commands.place_order import PlaceOrderCommand
from app.modules.trading.domain.entities import TradeOrder
from app.modules.trading.domain.events import OrderStateChanged
from app.modules.trading.domain.portfolio import Position
from app.modules.trading.domain.portfolio_ports import PositionRepository
from app.modules.trading.domain.ports import EventPublisher, OrderGateway, OrderRepository, RiskGate


class PlaceOrderService:
    def __init__(
        self,
        repository: OrderRepository,
        gateway: OrderGateway,
        risk_gate: RiskGate,
        clock: Clock,
        publisher: EventPublisher,
        positions: PositionRepository,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._risk_gate = risk_gate
        self._clock = clock
        self._publisher = publisher
        self._positions = positions

    async def execute(self, command: PlaceOrderCommand) -> Result[TradeOrder, str]:
        existing = await self._repository.get_by_client_order_id(command.client_order_id)
        if existing is not None:
            return Ok(existing)

        allowed, reason = await self._risk_gate.authorize(
            symbol=command.symbol,
            notional=command.quantity * command.price,
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
        except (ValueError, RuntimeError) as exc:
            return Err(str(exc))

        await self._repository.save(submitted)

        if submitted.status.value == "filled" and submitted.executed_price is not None:
            position = await self._positions.get(submitted.symbol)
            if position is None:
                position = Position.empty(submitted.symbol)
            await self._positions.save(
                position.apply_fill(
                    side=submitted.side.value,
                    quantity=submitted.quantity,
                    price=submitted.executed_price,
                )
            )

        await self._publisher.publish(
            OrderStateChanged(
                order_id=str(submitted.id),
                status=submitted.status,
                symbol=submitted.symbol,
            )
        )
        return Ok(submitted)
