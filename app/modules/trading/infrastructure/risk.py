from __future__ import annotations

from decimal import Decimal

from app.modules.risk.application.services import RiskService


class RiskServiceAdapter:
    def __init__(self, service: RiskService) -> None:
        self._service = service

    async def authorize(
        self,
        *,
        symbol: str,
        notional: object,
        equity: object,
    ) -> tuple[bool, str]:
        notional_decimal = Decimal(str(notional))
        equity_decimal = Decimal(str(equity))
        position_pct = notional_decimal / equity_decimal if equity_decimal else Decimal("1")
        decision = await self._service.check_order(
            symbol=symbol,
            notional=notional_decimal,
            equity=equity_decimal,
            daily_loss=Decimal("0"),
            position_pct=position_pct,
        )
        return decision.approved, decision.reason
