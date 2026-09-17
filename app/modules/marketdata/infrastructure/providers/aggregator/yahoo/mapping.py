"""Yahoo chart payload -> normalized domain Candle/Ticker (guarantee G8).

Vendor shapes stop here: only `Candle`/`Ticker` leave this module.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import ValidationError

from app.core.exceptions.taxonomy import MalformedDataError
from app.modules.marketdata.domain.entities import Candle, Symbol, Ticker, Timeframe
from app.modules.marketdata.infrastructure.providers.aggregator.yahoo.dtos import YahooChartResult

EXCHANGE = "yahoo"
_QUOTE_ALIASES = {"USDT": "USD", "USDC": "USD", "BUSD": "USD"}


def to_yahoo_symbol(symbol: Symbol) -> str:
    """`BTC/USDT` -> `BTC-USD`, `AAPL/USD` -> `AAPL-USD`."""
    base, _, quote = symbol.code.partition("/")
    return f"{base}-{_QUOTE_ALIASES.get(quote, quote)}"


def to_candles(
    chart: YahooChartResult,
    symbol: Symbol,
    timeframe: Timeframe,
    exchange: str = EXCHANGE,
) -> list[Candle]:
    if not chart.indicators.quote:
        raise MalformedDataError("yahoo chart carried no quote series", provider=EXCHANGE)
    timestamps = chart.timestamp or []
    series = chart.indicators.quote[0]
    rows = zip(
        timestamps,
        series.open,
        series.high,
        series.low,
        series.close,
        series.volume,
        strict=False,
    )
    candles = [
        candle
        for candle in (
            _row_to_candle(ts, o, h, low, close, volume, symbol, timeframe, exchange)
            for ts, o, h, low, close, volume in rows
        )
        if candle is not None
    ]
    if not candles:
        raise MalformedDataError("yahoo chart returned no usable candles", provider=EXCHANGE)
    return candles


def to_ticker(chart: YahooChartResult, symbol: Symbol, exchange: str = EXCHANGE) -> Ticker:
    """Best-effort ticker.

    The chart endpoint exposes no order book and no rolling 24h volume, so
    bid/ask collapse to the last price and `volume_24h` stays zero rather than
    inventing data.
    """
    meta = chart.meta
    last = meta.regularMarketPrice if meta.regularMarketPrice is not None else meta.chartPreviousClose
    observed_at = meta.regularMarketTime or (chart.timestamp[-1] if chart.timestamp else None)
    if last is None or observed_at is None:
        raise MalformedDataError("yahoo chart carried no tradable price", provider=EXCHANGE)
    price = Decimal(str(last))
    return Ticker(
        symbol=symbol,
        timestamp=datetime.fromtimestamp(observed_at, UTC),
        bid=price,
        ask=price,
        last=price,
        volume_24h=Decimal(0),
        exchange=exchange,
    )


def _row_to_candle(
    timestamp: int,
    open_: float | None,
    high: float | None,
    low: float | None,
    close: float | None,
    volume: float | None,
    symbol: Symbol,
    timeframe: Timeframe,
    exchange: str,
) -> Candle | None:
    if open_ is None or high is None or low is None or close is None:
        return None  # Yahoo pads session edges with nulls
    try:
        return Candle(
            symbol=symbol,
            timeframe=timeframe,
            opened_at=datetime.fromtimestamp(timestamp, UTC),
            open=Decimal(str(open_)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
            volume=Decimal(str(volume or 0)),
            exchange=exchange,
        )
    except (ValidationError, ArithmeticError, ValueError) as exc:
        raise MalformedDataError(
            f"yahoo candle normalization failed: {exc}",
            provider=exchange,
            cause=exc,
        ) from exc
