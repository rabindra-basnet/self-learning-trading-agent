---
name: backend-slice
description: How to add or modify a feature inside app/modules/. Domain-first workflow: entities, ports, use-case, adapter, presentation, DI.
---

# Backend Slice

Load this skill: when adding or modifying a feature inside `app/modules/<name>/`.

Reference: `docs/CONVENTIONS.md` for naming, typing, DoD. `docs/INTEGRATION-ARCHITECTURE.md` for port/adapter rules.

---

## Step 1: Identify the Module

Which module owns this? Existing: `auth`, `marketdata`, `signals`, `strategies`, `backtest`, `risk`.
New capability with its own vocabulary and events = new slice.

## Step 2: Work Outside-In

Order: domain -> ports -> use-case -> adapter -> presentation -> DI.

### domain/entities.py

Pydantic v2 models, `StrEnum`, provider-independent. `Decimal` for money.

```python
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel

class Candle(BaseModel):
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    timestamp: datetime
```

### domain/ports.py

`Protocol` classes naming capabilities, not vendors.

```python
from typing import Protocol

class CandleStore(Protocol):
    async def append(self, candles: list[Candle]) -> int: ...
    async def latest(self, symbol: str, n: int = 100) -> list[Candle]: ...
```

### domain/events.py

Only when cross-slice decoupling is needed.

```python
from app.core.messaging.bus import DomainEvent

class CandleReceived(DomainEvent):
    symbol: str
    count: int
```

### application/services.py

Constructor-injected ports, `Result[T, DomainError]` returns.

```python
from app.core.common.result import Ok, Result
from app.core.exceptions.taxonomy import DomainError

class CandleIngestService:
    def __init__(self, store: CandleStore, bus: EventBus) -> None:
        self._store = store
        self._bus = bus

    async def sync(self, symbol: str, limit: int = 100) -> Result[SyncSummary, DomainError]:
        candles = await self._source.fetch(symbol, limit=limit)
        stored = await self._store.append(candles)
        await self._bus.publish(CandleReceived(symbol=symbol, count=stored))
        return Ok(SyncSummary(stored=stored))
```

Check errors: `result.is_err` and `result.error_value()` / `result.ok_value()` as methods.
`Ok`/`Err` are factory functions. `isinstance(result, Err)` is ALWAYS False.

### infrastructure/providers/<vendor>/

Adapter structure:

```
config.py      vendor settings
client.py      raw transport (no domain types)
dtos.py        vendor shapes
mapping.py     DTO -> domain entity
errors.py      vendor exceptions -> DomainError subclass
adapter.py     implements the port
```

Every vendor failure maps to exactly one `DomainError` subclass. SDK exceptions never cross the boundary.

### presentation/routes.py + schemas.py

Transport shapes only. Resolve services from container. Translate `Err` -> `HTTPException`.

```python
from fastapi import APIRouter, HTTPException, Request
from app.core.exceptions.taxonomy import http_status_for

router = APIRouter(prefix="/candles", tags=["candles"])

@router.get("/")
async def list_candles(request: Request, symbol: str = "BTC/USDT"):
    service = request.app.state.container.resolve(CandleQueryService)
    result = await service.latest(symbol)
    if result.is_err:
        error = result.error_value()
        raise HTTPException(status_code=http_status_for(error), detail=error.message)
    return result.ok_value()
```

## Step 3: Composition Root

`app/di.py` - register services under the slice's comment block.
`app/routers.py` - include the router.

## Step 4: Import-Linter Contracts

Edit `pyproject.toml` in three places:
1. New slice's own contract.
2. Add new slice to every other slice's `forbidden_modules`.
3. Add new slice's `domain`/`application` to provider-free contract's `source_modules`.

Verify: `uv run lint-imports`
