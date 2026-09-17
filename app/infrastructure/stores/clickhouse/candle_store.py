"""ClickHouse CandleStore adapter — implements CandleStore against market_candles.

Uses the connection's native `AsyncClient` (no to_thread, no sync driver).
Runs against real ClickHouse in integration tests (testcontainers).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from app.core.logging.setup import get_logger
from app.infrastructure.capability.database.clickhouse import ClickHouseConnection
from app.modules.marketdata.domain.entities import Candle, Symbol, Timeframe

logger = get_logger("stores.clickhouse")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


_DDL = """
CREATE TABLE IF NOT EXISTS market_candles (
    symbol       LowCardinality(String),
    timeframe    LowCardinality(String),
    opened_at    DateTime64(3, 'UTC'),
    open         Decimal128(18),
    high         Decimal128(18),
    low          Decimal128(18),
    close        Decimal128(18),
    volume       Decimal128(18),
    exchange     LowCardinality(String)
) ENGINE = ReplacingMergeTree(opened_at)
ORDER BY (symbol, timeframe, opened_at)
PARTITION BY toYYYYMM(opened_at)
"""

_INSERT = """
INSERT INTO market_candles (symbol, timeframe, opened_at, open, high, low, close, volume, exchange)
VALUES
"""

_SELECT = """
SELECT symbol, timeframe, opened_at, open, high, low, close, volume, exchange
FROM market_candles
FINAL
WHERE symbol = %(symbol)s AND timeframe = %(timeframe)s
  AND opened_at >= %(start)s AND opened_at <= %(end)s
ORDER BY opened_at
"""

_SELECT_LATEST = """
SELECT symbol, timeframe, opened_at, open, high, low, close, volume, exchange
FROM market_candles
FINAL
WHERE symbol = %(symbol)s AND timeframe = %(timeframe)s
ORDER BY opened_at DESC
LIMIT %(limit)s
"""


class ClickHouseCandleStore:
    async def __connect__(self) -> None:
        pass

    async def __disconnect__(self) -> None:
        pass

    def __init__(self, connection: ClickHouseConnection) -> None:
        self._connection = connection
        self._initialized = False

    async def _ensure_table(self) -> None:
        if self._initialized:
            return
        async with self._connection.client_scope() as client:
            await client.command(_DDL)
        self._initialized = True

    async def append(self, candles: Sequence[Candle]) -> int:
        if not candles:
            return 0
        await self._ensure_table()
        rows = [
            [
                c.symbol.code,
                c.timeframe.value,
                _as_utc(c.opened_at),
                float(c.open),
                float(c.high),
                float(c.low),
                float(c.close),
                float(c.volume),
                c.exchange,
            ]
            for c in candles
        ]
        async with self._connection.client_scope() as client:
            await client.insert("market_candles", rows)
        return len(rows)

    async def query_range(self, symbol: Symbol, timeframe: Timeframe, start: datetime, end: datetime) -> list[Candle]:
        await self._ensure_table()
        async with self._connection.client_scope() as client:
            result = await client.query(
                _SELECT,
                parameters=dict(symbol=symbol.code, timeframe=timeframe.value, start=_as_utc(start), end=_as_utc(end)),
            )
        return [self._row_to_candle(r) for r in result.result_rows]

    async def latest(self, symbol: Symbol, timeframe: Timeframe, n: int = 100) -> list[Candle]:
        await self._ensure_table()
        async with self._connection.client_scope() as client:
            result = await client.query(
                _SELECT_LATEST,
                parameters=dict(symbol=symbol.code, timeframe=timeframe.value, limit=n),
            )
        return [self._row_to_candle(r) for r in reversed(result.result_rows)]

    @staticmethod
    def _row_to_candle(row: Sequence[Any]) -> Candle:
        return Candle(
            symbol=Symbol.of(row[0]),
            timeframe=Timeframe(row[1]),
            opened_at=_as_utc(row[2]),
            open=row[3],
            high=row[4],
            low=row[5],
            close=row[6],
            volume=row[7],
            exchange=row[8],
        )
