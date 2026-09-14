"""marketdata API schemas (transport layer — never provider types)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SyncRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    limit: int = Field(default=100, le=1000)


class CandleSummary(BaseModel):
    timeframe: str
    symbol: str
    appended: int
    fetched: int
