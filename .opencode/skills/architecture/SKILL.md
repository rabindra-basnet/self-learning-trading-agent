---
name: architecture
description: Architecture rules for this repo. Load before any code change. Covers dependency direction, module structure, ports/adapters, cross-slice rules, anti-patterns.
---

# Architecture Rules

Load this skill: ALWAYS, before any code change in this repository.

Reference: `docs/INTEGRATION-ARCHITECTURE.md` for ports & adapters guarantee matrix.

---

## Dependency Direction (CI-enforced)

```
Presentation -> Application -> Domain
Infrastructure -> Domain Ports
```

Domain never imports: FastAPI, PostgreSQL, ClickHouse, Redis, CCXT, httpx, pandas, SQLAlchemy, any SDK.
Application never imports: concrete infrastructure, SDKs, frameworks.
Presentation never imports: other slices, repositories, Redis, database.
Infrastructure may import: domain ports, core, any SDK needed to implement the port.

## Module Structure

Each module lives in `app/modules/<name>/`:

```
presentation/     routes.py, schemas.py       (inbound adapter)
application/      services.py                 (use-cases)
domain/           entities.py, ports.py, events.py
infrastructure/   providers/, stores/         (outbound adapters)
contracts/        __init__.py                 (public surface for other slices)
```

## Cross-Slice Rules

- A slice may import ONLY another slice's `contracts/`.
- Prefer domain events over direct calls for cross-module communication.
- `import-linter` enforces this in CI. Violation = red build.

## Shared Boundaries

- `app/core/` = genuinely shared kernel (Result, errors, logging, bus, config).
- `app/infrastructure/` = shared adapters (Postgres, ClickHouse, Redis, bus, outbox).
- Feature-specific code stays in its module, NOT in core or shared infrastructure.

## Ports and Adapters

A port is a `Protocol` in `domain/ports.py` naming a capability:

```python
class MarketDataProvider(Protocol):
    async def get_candles(self, symbol: str, ...) -> list[Candle]: ...
```

An adapter implements it in `infrastructure/providers/<vendor>/`:

```python
class BinanceMarketAdapter:
    async def get_candles(self, symbol: str, ...) -> list[Candle]:
        raw = await self._client.fetch_ohlcv(symbol, ...)
        return [map_to_candle(c) for c in raw]
```

Inner code knows the port. Infrastructure knows the implementation.

## Anti-Patterns to Avoid

- GenericRepository, BaseService, UseCaseFactory, ManagerFactory
- One interface per class, one repository per table, one event per method
- Feature code in `core/utils/` or `core/helpers/`
- SDK types leaking into domain/application/contracts
- Business logic in presentation routes or workers
