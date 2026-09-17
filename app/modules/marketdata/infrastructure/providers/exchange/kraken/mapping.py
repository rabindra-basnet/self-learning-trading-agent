"""Kraken payload -> normalized domain Candle/Ticker (guarantee G8)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from app.core.exceptions.taxonomy import MalformedDataError
from app.modules.marketdata.domain.entities import Candle, Symbol, Ticker, Timeframe

EXCHANGE = "kraken"
_BASE_ALIASES = {"BTC": "XBT", "DOGE": "XDG"}
_OHLC_COLUMNS = 7  # time, open, high, low, close, vwap, volume


def to_kraken_pair(symbol: Symbol) -> str:
    """`BTC/USDT` -> `XBTUSDT`, `ETH/USD` -> `ETHUSD`."""
    base, _, quote = symbol.code.partition("/")
    return f"{_BASE_ALIASES.get(base, base)}{quote}"


def first_entry(result: Mapping[str, Any]) -> Mapping[str, Any]:
    """Kraken keys results by its own normalized pair name; single-pair calls have one."""
    for key, value in result.items():
        if key != "last" and isinstance(value, Mapping):
            return value
    raise MalformedDataError("kraken response carried no result entry", provider=EXCHANGE)


def to_candles(
    rows: Sequence[Sequence[Any]],
    symbol: Symbol,
    timeframe: Timeframe,
    exchange: str = EXCHANGE,
) -> list[Candle]:
    candles: list[Candle] = []
    for row in rows:
        if len(row) < _OHLC_COLUMNS:
            continue
        try:
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    opened_at=datetime.fromtimestamp(int(row[0]), UTC),
                    open=Decimal(str(row[1])),
                    high=Decimal(str(row[2])),
                    low=Decimal(str(row[3])),
                    close=Decimal(str(row[4])),
                    volume=Decimal(str(row[6])),
                    exchange=exchange,
                )
            )
        except (ValidationError, ArithmeticError, TypeError, ValueError) as exc:
            raise MalformedDataError(
                f"kraken OHLC normalization failed: {exc}",
                provider=exchange,
                cause=exc,
            ) from exc
    if not candles:
        raise MalformedDataError("kraken OHLC returned no usable rows", provider=EXCHANGE)
    return candles


def to_ticker(
    entry: Mapping[str, Any],
    symbol: Symbol,
    observed_at: datetime,
    exchange: str = EXCHANGE,
) -> Ticker:
    try:
        return Ticker(
            symbol=symbol,
            timestamp=observed_at,
            bid=Decimal(str(entry["b"][0])),
            ask=Decimal(str(entry["a"][0])),
            last=Decimal(str(entry["c"][0])),
            volume_24h=Decimal(str(entry["v"][1])),
            exchange=exchange,
        )
    except (ValidationError, ArithmeticError, KeyError, IndexError, TypeError) as exc:
        raise MalformedDataError(
            f"kraken ticker normalization failed: {exc}",
            provider=exchange,
            cause=exc,
        ) from exc
