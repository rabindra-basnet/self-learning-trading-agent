from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.modules.auth.application.services import CurrentUserService
from magic_di.fastapi import Provide
from app.modules.auth.domain.entities import User


async def get_current_user(
    request: Request,
    current_user: Provide[CurrentUserService],
) -> User:
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing_token")
    result = await current_user.resolve(token)
    if result.is_err:
        raise HTTPException(status_code=401, detail=result.error_value().message)
    return result.ok_value()
from app.modules.trading.application.commands.place_order import PlaceOrderCommand
from app.modules.trading.application.services.place_order import PlaceOrderService
from app.modules.trading.presentation.dependencies import (
    get_live_place_order_service,
    get_place_order_service,
)
from app.modules.trading.presentation.schemas import OrderResponse, PlaceOrderRequest

router = APIRouter(prefix="/trading/orders", tags=["trading"])


def _command(request: PlaceOrderRequest) -> PlaceOrderCommand:
    return PlaceOrderCommand(
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        price=request.price,
        client_order_id=request.client_order_id,
        equity=request.equity,
    )


@router.post("/paper", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_paper_order(
    request: PlaceOrderRequest,
    service: PlaceOrderService = Depends(get_place_order_service),
) -> OrderResponse:
    result = await service.execute(_command(request))
    if result.is_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.error_value())
    return OrderResponse.from_domain(result.ok_value())


@router.post("/live", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_live_order(
    request: PlaceOrderRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: PlaceOrderService = Depends(get_live_place_order_service),
) -> OrderResponse:
    result = await service.execute(_command(request))
    if result.is_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.error_value())
    return OrderResponse.from_domain(result.ok_value())
