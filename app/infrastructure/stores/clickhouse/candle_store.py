"""ClickHouse CandleStore adapter — implements CandleStore with ReplacingMergeTree.

Wraps `clickhouse_connect` (sync) in `asyncio.to_thread`; handles table DDL once.
Run against real ClickHouse in integration tests (testcontainers).
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime

import clickhouse_connect.driver.async_client as ch_async  # type: ignore[import-untyped]
from app.modules.marketdata.domain.entities import Candle, Symbol, Timeframe

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
    def __init__(
        self,
        host: str,
        port: int = 8123,
        user: str = "default",
        password: str = "",
        database: str = "trading",
    ) -> None:
        self._cfg = dict(host=host, port=port, username=user, password=password, database=database)
        self._client: ch_async.Client | None = None
        self._initialized = False

    async def _get_client(self) -> ch_async.Client:
        if self._client is None:
            self._client = ch_async.Client(**self._cfg)
        if not self._initialized:
            await asyncio.to_thread(self._client.command, _DDL)
            self._initialized = True
        return self._client

    async def append(self, candles: Sequence[Candle]) -> int:
        if not candles:
            return 0
        client = await self._get_client()
        rows = [
            [
                c.symbol.code,
                c.timeframe.value,
                c.opened_at.replace(tzinfo=None),
                float(c.open),
                float(c.high),
                float(c.low),
                float(c.close),
                float(c.volume),
                c.exchange,
            ]
            for c in candles
        ]
        await asyncio.to_thread(client.insert, "market_candles", rows)
        return len(rows)

    async def query_range(self, symbol: Symbol, timeframe: Timeframe, start: datetime, end: datetime) -> list[Candle]:
        client = await self._get_client()
        result = await asyncio.to_thread(
            client.query,
            _SELECT,
            parameters=dict(symbol=symbol.code, timeframe=timeframe.value, start=start, end=end),
        )
        return [self._row_to_candle(r) for r in result.result_rows]

    async def latest(self, symbol: Symbol, timeframe: Timeframe, n: int = 100) -> list[Candle]:
        client = await self._get_client()
        result = await asyncio.to_thread(
            client.query,
            _SELECT_LATEST,
            parameters=dict(symbol=symbol.code, timeframe=timeframe.value, limit=n),
        )
        return [self._row_to_candle(r) for r in reversed(result.result_rows)]

    @staticmethod
    def _row_to_candle(row: tuple) -> Candle:
        return Candle(
            symbol=Symbol.of(row[0]),
            timeframe=Timeframe(row[1]),
            opened_at=row[2],
            open=row[3],
            high=row[4],
            low=row[5],
            close=row[6],
            volume=row[7],
            exchange=row[8],
        )
