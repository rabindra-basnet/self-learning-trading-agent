"""Binance vendor-specific DTOs (raw payload models — never exported from boundary)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

# A Binance kline is a 12-element list.
# [open_time_ms, open, high, low, close, volume, close_time_ms, quote_vol, trades, taker_base, taker_quote, ignore]


class RawKline(BaseModel):
    open_time_ms: int
    open: str
    high: str
    low: str
    close: str
    volume: str

    @classmethod
    def of(cls, row: list[Any]) -> RawKline:
        if isinstance(row, (list, tuple)) and len(row) >= 6:
            return cls(
                open_time_ms=int(row[0]),
                open=str(row[1]),
                high=str(row[2]),
                low=str(row[3]),
                close=str(row[4]),
                volume=str(row[5]),
            )
        raise ValueError(f"malformed binance kline row: {row!r}")
