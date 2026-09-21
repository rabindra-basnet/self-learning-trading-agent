from __future__ import annotations

from fastapi import Depends

from app.core.common.clock import Clock
from app.core.messaging.bus import EventBus
from app.modules.risk.application.services import RiskService
from app.modules.trading.application.services.place_order import PlaceOrderService
from app.modules.trading.infrastructure.gateways.paper import PaperOrderGateway
from app.modules.trading.infrastructure.repositories.in_memory import InMemoryOrderRepository
from app.modules.trading.infrastructure.risk import RiskServiceAdapter

_repository = InMemoryOrderRepository()
_gateway = PaperOrderGateway()


def get_place_order_service(
    clock: Clock,
    risk_service: RiskService,
    event_bus: EventBus,
) -> PlaceOrderService:
    return PlaceOrderService(
        repository=_repository,
        gateway=_gateway,
        risk_gate=RiskServiceAdapter(risk_service),
        clock=clock,
        publisher=event_bus,
    )
