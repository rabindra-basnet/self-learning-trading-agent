"""Binance → domain mapping. Normalizes vendor payloads into domain Candle/Ticker.

All provider formats are validated here; failures raise MalformedDataError —
vendor exceptions never reach the domain.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import ValidationError

from app.core.exceptions.taxonomy import MalformedDataError
from app.modules.marketdata.domain.entities import Candle, Symbol, Ticker, Timeframe
from app.modules.marketdata.infrastructure.providers.exchange.binance.dtos import RawKline


def to_candle(kline: RawKline, symbol: Symbol, timeframe: Timeframe, exchange: str) -> Candle:
    try:
        return Candle(
            symbol=symbol,
            timeframe=timeframe,
            opened_at=datetime.fromtimestamp(kline.open_time_ms / 1000.0, UTC),
            open=Decimal(kline.open),
            high=Decimal(kline.high),
            low=Decimal(kline.low),
            close=Decimal(kline.close),
            volume=Decimal(kline.volume),
            exchange=exchange,
        )
    except (ValidationError, ArithmeticError) as exc:
        raise MalformedDataError(f"binance kline normalization failed: {exc}", provider="binance", cause=exc) from exc


def to_ticker(raw: dict, symbol: Symbol, exchange: str) -> Ticker:
    try:
        return Ticker(
            symbol=symbol,
            timestamp=datetime.fromtimestamp(int(raw["closeTime"]) / 1000.0, UTC),
            bid=Decimal(str(raw.get("bidPrice", "0"))),
            ask=Decimal(str(raw.get("askPrice", "0"))),
            last=Decimal(str(raw.get("lastPrice", "0"))),
            volume_24h=Decimal(str(raw.get("quoteVolume", "0"))),
            exchange=exchange,
        )
    except (ValidationError, ArithmeticError, KeyError) as exc:
        raise MalformedDataError(f"binance ticker normalization failed: {exc}", provider="binance", cause=exc) from exc
