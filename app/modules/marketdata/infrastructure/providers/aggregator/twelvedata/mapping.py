"""Twelve Data payload -> normalized domain Candle/Ticker (guarantee G8)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from app.core.exceptions.taxonomy import MalformedDataError
from app.modules.marketdata.domain.entities import Candle, Symbol, Ticker, Timeframe
from app.modules.marketdata.infrastructure.providers.aggregator.twelvedata.dtos import (
    TwelveQuote,
    TwelveValue,
)

EXCHANGE = "twelvedata"
_INTRADAY_FORMAT = "%Y-%m-%d %H:%M:%S"
_DAILY_FORMAT = "%Y-%m-%d"


def parse_datetime(raw: str) -> datetime:
    """Twelve Data stamps intraday rows as UTC and daily rows as date-only."""
    text = raw.strip()
    for fmt in (_INTRADAY_FORMAT, _DAILY_FORMAT):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    raise MalformedDataError(f"unparseable twelve data timestamp: {raw!r}", provider=EXCHANGE)


def to_candles(
    values: Sequence[TwelveValue],
    symbol: Symbol,
    timeframe: Timeframe,
    exchange: str = EXCHANGE,
) -> list[Candle]:
    """Twelve Data returns newest-first; the domain expects ascending time."""
    candles: list[Candle] = []
    for value in reversed(values):
        try:
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    opened_at=parse_datetime(value.datetime),
                    open=Decimal(value.open),
                    high=Decimal(value.high),
                    low=Decimal(value.low),
                    close=Decimal(value.close),
                    volume=Decimal(value.volume) if value.volume else Decimal(0),
                    exchange=exchange,
                )
            )
        except (ValidationError, ArithmeticError, InvalidOperation) as exc:
            raise MalformedDataError(
                f"twelve data candle normalization failed: {exc}",
                provider=exchange,
                cause=exc,
            ) from exc
    if not candles:
        raise MalformedDataError("twelve data returned no usable candles", provider=EXCHANGE)
    return candles


def to_ticker(
    quote: TwelveQuote,
    symbol: Symbol,
    observed_at: datetime,
    exchange: str = EXCHANGE,
) -> Ticker:
    """Best-effort ticker: `/quote` exposes no order book, so bid/ask mirror last."""
    if not quote.close:
        raise MalformedDataError("twelve data quote carried no close price", provider=EXCHANGE)
    try:
        price = Decimal(quote.close)
    except (ArithmeticError, InvalidOperation) as exc:
        raise MalformedDataError(
            f"twelve data quote normalization failed: {exc}",
            provider=exchange,
            cause=exc,
        ) from exc
    return Ticker(
        symbol=symbol,
        timestamp=datetime.fromtimestamp(quote.timestamp, UTC) if quote.timestamp else observed_at,
        bid=price,
        ask=price,
        last=price,
        volume_24h=Decimal(quote.volume) if quote.volume else Decimal(0),
        exchange=exchange,
    )
