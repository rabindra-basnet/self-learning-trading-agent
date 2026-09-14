"""marketdata domain: normalized models (provider-independent)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class Timeframe(StrEnum):
    M1 = "1m"
    M5 = "5m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class Symbol(BaseModel):
    """Normalized symbol — e.g. `code="BTC/USDT"` on exchange `"binance"`."""

    code: str = Field(pattern=r"^[A-Z0-9]+/[A-Z0-9]+$")
    exchange: str = ""

    @classmethod
    def of(cls, code: str, exchange: str = "") -> Symbol:
        return cls(code=code.upper(), exchange=exchange.lower())


class Candle(BaseModel):
    symbol: Symbol
    timeframe: Timeframe
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    exchange: str = ""


class Ticker(BaseModel):
    symbol: Symbol
    timestamp: datetime
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume_24h: Decimal
    exchange: str = ""
