from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.trading.application.commands.place_order import PlaceOrderCommand
from app.modules.trading.application.services.place_order import PlaceOrderService
from app.modules.trading.presentation.dependencies import get_place_order_service
from app.modules.trading.presentation.schemas import OrderResponse, PlaceOrderRequest

router = APIRouter(prefix="/trading/orders", tags=["trading"])


@router.post("/paper", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_paper_order(
    request: PlaceOrderRequest,
    service: PlaceOrderService = Depends(get_place_order_service),
) -> OrderResponse:
    result = await service.execute(
        PlaceOrderCommand(
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=request.price,
            client_order_id=request.client_order_id,
            equity=request.equity,
        )
    )

    if result.is_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.error_value())

    return OrderResponse.from_domain(result.ok_value())
