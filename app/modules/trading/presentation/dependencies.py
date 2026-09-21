from __future__ import annotations

from fastapi import Request

from app.core.common.clock import Clock
from app.core.messaging.bus import EventBus
from app.modules.risk.application.services import RiskService
from app.modules.trading.application.services.place_order import PlaceOrderService
from app.modules.trading.infrastructure.gateways.paper import PaperOrderGateway
from app.modules.trading.infrastructure.repositories.in_memory import InMemoryOrderRepository
from app.modules.trading.infrastructure.risk import RiskServiceAdapter

_repository = InMemoryOrderRepository()
_gateway = PaperOrderGateway()


def _resolve(request: Request, interface: type):
    injector = request.app.state.injector
    return next(iter(injector.get_dependencies_by_interface(interface)))


def get_place_order_service(request: Request) -> PlaceOrderService:
    return PlaceOrderService(
        repository=_repository,
        gateway=_gateway,
        risk_gate=RiskServiceAdapter(_resolve(request, RiskService)),
        clock=_resolve(request, Clock),
        publisher=_resolve(request, EventBus),
    )
