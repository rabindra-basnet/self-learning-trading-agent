"""marketdata application: use-cases. Depend only on ports; normalize at boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.common.result import Err, Ok, Result
from app.core.exceptions.taxonomy import DomainError, MalformedDataError
from app.core.logging.setup import get_logger
from app.core.messaging.bus import DomainEvent, EventBus
from app.modules.marketdata.domain.entities import Candle, Symbol, Timeframe
from app.modules.marketdata.domain.events import CandleReceived
from app.modules.marketdata.domain.ports import CandleStore, MarketDataSource, TimeSource

logger = get_logger("marketdata.service")


@dataclass(frozen=True, slots=True)
class SyncSummary:
    symbol: Symbol
    timeframe: Timeframe
    fetched: int
    appended: int
    duplicates: int

    @property
    def ok(self) -> bool:
        return self.appended > 0


class CandleIngestService:
    def __init__(
        self,
        market_data: MarketDataSource,
        store: CandleStore,
        bus: EventBus,
        clock: TimeSource,
    ) -> None:
        self._market_data = market_data
        self._store = store
        self._bus = bus
        self._clock = clock

    async def sync(
        self,
        *,
        symbol: Symbol,
        timeframe: Timeframe,
        since: datetime | None = None,
        limit: int = 500,
    ) -> Result[SyncSummary, DomainError]:
        try:
            candles = await self._market_data.fetch_candles(symbol, timeframe, since=since, limit=limit)
        except DomainError as exc:
            return Err(exc)
        if not candles:
            return Ok(SyncSummary(symbol=symbol, timeframe=timeframe, fetched=0, appended=0, duplicates=0))
        candles = self._dedupe(candles)
        appended = await self._store.append(candles)
        event: DomainEvent = CandleReceived(
            symbol=symbol,
            timeframe=timeframe.value,
            candles=candles,
        )
        await self._bus.publish(event)
        logger.info(
            "candles_synced",
            symbol=symbol.code,
            timeframe=timeframe.value,
            appended=appended,
            fetched=len(candles),
        )
        return Ok(
            SyncSummary(
                symbol=symbol,
                timeframe=timeframe,
                fetched=len(candles),
                appended=appended,
                duplicates=max(0, len(candles) - appended),
            )
        )

    async def ingest_raw(self, candles: list[Candle]) -> None:
        """Boundary convenience for tests/recorded feeds: assumes normalized input."""
        if not candles:
            return
        if any(not c.symbol.code for c in candles):
            raise MalformedDataError("candle missing symbol", provider="marketdata")
        await self._store.append(candles)
        for candle in candles:
            await self._bus.publish(
                CandleReceived(symbol=candle.symbol, timeframe=candle.timeframe.value, candles=[candle])
            )

    @staticmethod
    def _dedupe(candles: list[Candle]) -> list[Candle]:
        seen: set[tuple[str, str, int]] = set()
        unique: list[Candle] = []
        for c in candles:
            key = (c.symbol.code, c.timeframe.value, int(c.opened_at.timestamp()))
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique


class CandleQueryService:
    def __init__(self, store: CandleStore) -> None:
        self._store = store

    async def range(self, symbol: Symbol, timeframe: Timeframe, start: datetime, end: datetime) -> list[Candle]:
        return await self._store.query_range(symbol, timeframe, start, end)

    async def latest(self, symbol: Symbol, timeframe: Timeframe, n: int = 100) -> list[Candle]:
        return await self._store.latest(symbol, timeframe, n)
