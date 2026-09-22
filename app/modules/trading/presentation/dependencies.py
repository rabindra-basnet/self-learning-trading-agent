from __future__ import annotations

from fastapi import Request

from app.core.common.clock import Clock
from app.core.config.settings import Settings
from app.core.messaging.bus import EventBus
from app.modules.risk.application.services import RiskService
from app.modules.trading.application.services.place_order import PlaceOrderService
from app.modules.trading.domain.portfolio_ports import PositionRepository
from app.modules.trading.infrastructure.gateways.ccxt_gateway import CcxtOrderGateway
from app.modules.trading.infrastructure.gateways.factory import build_ccxt_exchange
from app.modules.trading.infrastructure.gateways.paper import PaperOrderGateway
from app.modules.trading.infrastructure.repositories.in_memory import InMemoryOrderRepository
from app.modules.trading.infrastructure.risk import RiskServiceAdapter

_repository = InMemoryOrderRepository()
_paper_gateway = PaperOrderGateway()
_live_gateway: CcxtOrderGateway | None = None


def _resolve(request: Request, interface: type):
    injector = request.app.state.injector
    return next(iter(injector.get_dependencies_by_interface(interface)))


def get_place_order_service(request: Request) -> PlaceOrderService:
    return PlaceOrderService(
        repository=_repository,
        gateway=_paper_gateway,
        risk_gate=RiskServiceAdapter(_resolve(request, RiskService)),
        clock=_resolve(request, Clock),
        publisher=_resolve(request, EventBus),
        positions=_resolve(request, PositionRepository),
    )


def get_live_place_order_service(request: Request) -> PlaceOrderService:
    global _live_gateway

    settings = _resolve(request, Settings)
    if settings.trading_execution_mode != "live":
        raise RuntimeError("live_trading_disabled")

    if not settings.trading_api_key.get_secret_value() or not settings.trading_api_secret.get_secret_value():
        raise RuntimeError("trading_exchange_credentials_missing")

    if _live_gateway is None:
        exchange = build_ccxt_exchange(
            settings.trading_exchange,
            settings.trading_api_key.get_secret_value(),
            settings.trading_api_secret.get_secret_value(),
        )
        _live_gateway = CcxtOrderGateway(exchange)

    return PlaceOrderService(
        repository=_repository,
        gateway=_live_gateway,
        risk_gate=RiskServiceAdapter(_resolve(request, RiskService)),
        clock=_resolve(request, Clock),
        publisher=_resolve(request, EventBus),
        positions=_resolve(request, PositionRepository),
    )
