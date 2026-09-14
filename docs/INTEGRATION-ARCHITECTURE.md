# Integration Architecture — Ports & Adapters (Hexagonal)

Status: DRAFT — approved-in-principle · Supplements `docs/SYSTEM-DESIGN.md` and `docs/SDLC-PLAN.md` §2

## 0. Scope

Every third-party integration is **completely isolated** from core/domain logic:

exchanges (Binance, Kraken, Coinbase), brokers, market-data providers, News APIs, RSS/GDELT, Reddit/X, alternative-data providers, on-chain APIs, LLM/AI providers, databases, Redis, Kafka/Redpanda, object storage, notification services, authentication providers, monitoring systems, schedulers, and any future service.

## 1. Principles & Guarantees

| # | Guarantee |
|---|---|
| G1 | **Zero third-party imports in domain.** The core depends only on Python stdlib + our own contracts. No SDK, provider, framework, or infra technology appears in `domain/` or `application/`. |
| G2 | **Capability contracts, not vendor names.** Ports are named by business capability (`MarketDataSource`, `OrderGateway`, `NewsProvider`, `LLMReasoner`, `CandleStore`, `EventBus`, `Notifier`, …), never `BinanceAPI`. |
| G3 | **Adapters live only in infrastructure.** Third-party implementations exist exclusively in `app/infrastructure/providers/<capability>/<vendor>/` (and infrastructure stores/bridges). |
| G4 | **Replacement = infra + config only.** Swapping Binance→Kraken, NewsAPI→RSS/GDELT, Redis→Kafka, OpenAI→Zen/local never touches strategies, domain services, AI agents, or business logic. |
| G5 | **New provider = new adapter package + config entry**, plus satisfying the port's contract suite. No architectural change, no domain change. |
| G6 | **Boundary owns provider-specific behaviour.** Each integration boundary is fully responsible for its SDK/API models, auth, config, rate limiting, retries, timeouts, circuit breaking, pagination, error mapping, idempotency, serialization, and vendor quirks. |
| G7 | **Composition & DI, not generic inheritance.** Adapters are concrete classes composing small shared tools (retry, breaker, mapping). No mega `BaseExchangeAdapter` hierarchy, no speculative generic Adapter/Strategy base classes. |
| G8 | **Normalize at the boundary.** External data is mapped to internal domain models/events inside the adapter before anything else sees it. Domain types never appear in provider payloads and vice-versa. |

## 2. Dependency Direction

```
┌─ driving (inbound) ──────────────┐        ┌─ driven (outbound) ───────────────┐
│  web/ · API routes · WS ·       │        │  infrastructure/providers/       │
│  message consumers · cli        │        │  <capability>/<vendor>/adapter.py│
└──────────────┬──────────────────┘        ▲   (implements domain port)       │
               │ calls                     │   e.g. exchange/binance,          │
               ▼ implements                │        llm/zen, news/newsapi      │
   ┌─────────────────────────────┐   implements │        notify/slack, …       │
   │  application/ (use-cases)   │──────────────┘  infrastructure/stores/      │
   │  depends ONLY on ports      │                 infrastructure/buses/       │
   └──────────────┬──────────────┘                 infrastructure/bridges/     │
                  ▼ implements/uses                infrastructure/tooling/     │
   ┌─────────────────────────────┐                        (retry, breaker, …)  │
   │  domain/  entities · ports  │                                           │
   └──────────────┬──────────────┘                                           │
                  ▲                                                            │
   ┌──────────────┴──────────────┐                                            │
   │  core/ (pure helpers too)   │  ← never imports modules, providers, SDKs  │
   └─────────────────────────────┘                                            │
```

Rules (markers passed to `import-linter`, CI-enforced):
- `domain → ⌀` (nothing; may import `core` pure types only)
- `application → domain, core, itself`
- `api(inbound) → application` (and may own request/response schema only)
- `infrastructure → domain ports, core tooling` (NEVER the reverse: domain/app must not import infrastructure)
- `core → ⌀` (no slices, no providers, no frameworks beyond stdlib + pure libs)
- `modules/sliceA → modules/sliceB ⌀` (only `contracts/` events/commands, via bus)

## 3. Ports (domain contracts by capability)

| Port (in `domain/ports.py`) | Capability | Sample methods | Adapters (present/future) |
|---|---|---|---|
| `MarketDataSource` | live & historical market data | `stream_candles()`, `get_candles()`, `get_tickers()` | `exchange/binance`, `exchange/kraken`, `exchange/coinbase` |
| `OrderGateway` | submit/manage orders | `submit_order()`, `cancel_order()`, `get_order()`, `stream_order_updates()` | `exchange/binance`, `broker/alpaca`, `broker/oanda` |
| `AccountFacade` | balances/positions | `get_balances()`, `get_positions()`, `get_equity()` | above + `paper/simulator` |
| `NewsProvider` | news ingestion | `fetch_news(filter) → list[NewsArticle]` | `news/newsapi`, `news/rss`, `news/gdelt` |
| `SocialFeed` | social sentiment | `fetch_posts(query) → list[SocialPost]` | `social/reddit`, `social/x` |
| `AltDataFeed` | alternative data | `fetch_snapshot() → AltSnapshot` | `alt/fear_greed`, `alt/whale_watch`, `chain/etherscan` |
| `LLMReasoner` | LLM text reasoning | `analyze(context) → AnalysisResult` | `llm/zen`, `llm/openai`, `llm/anthropic`, `llm/local` |
| `CandleStore` | appends/queries candles | `append()`, `query_range()`, `latest()` | `stores/clickhouse`, `stores/in_memory` (tests) |
| `TradeStore` | PnL/trade analytics | `append_fill()`, `query_pnl()` | `stores/clickhouse` |
| `Repository[T]` | transactional CRUD | `save/get/list` | `stores/postgres` |
| `EventBus` | publish/subscribe events | `publish()`, `subscribe()`, `consume_group()` | `buses/redis_streams`, `buses/kafka`, `buses/in_memory` |
| `Outbox` | reliable event emission | `append()`, `mark_dispatched()`, `next_undispatched()` | `stores/postgres` (+ `core` tx helper) |
| `ObjectStore` | blob storage | `put/get/delete` | `cloudflare/r2`, `aws/s3`, `minio` |
| `Notifier` | alerts to humans | `send(channel, msg)` | `notify/slack`, `notify/telegram`, `notify/email`, `notify/webhook` |
| `Authenticator` | identity/token lifecycle | `issue()`, `verify()`, `refresh()` | `auth/jwt`, `auth/oauth` (provider) |
| `Tracer`, `Meter` | observability | `span()`, `counter()` | `otel/collector`, `otel/noop` |
| `Scheduler` | background/scheduled jobs | `schedule(job, cron)` | `scheduler/apscheduler`, `scheduler/cloudflare_cron` |
| `KVStore` | cache | `get/set/delete` | `kv/redis`, `kv/cloudflare_kv` |
| `MessageQueue`(opt.) | work queue | `enqueue()`, `claim()` | `queue/kafka`, `queue/redpanda`, `queue/redis` |

Persistence ports are **capability-consumer-facing** (how slices read/write *their* data), so swapping ClickHouse→TimescaleDB only changes `stores/` + config; swapping PostgreSQL→D1 only changes `stores/`.

## 4. Hexagonal slice layout

```
app/modules/<slice>/
├─ domain/            # entities · value objects · ports · domain events  (zero infra imports)
│   ├─ entities.py    # Candle, Ticker, Order, Fill, NewsArticle, AnalysisResult, …  (G8)
│   ├─ ports.py       # capability interfaces (G2)
│   └─ events.py      # CandleReceived, FillRecorded, …   (normalized domain events)
├─ application/       # use-cases/services; depend only on domain ports + core
│   └─ services.py
├─ infrastructure/    # OUTBOUND ADAPTERS ONLY (G3)
│   └─ providers/<capability>/<vendor>/   # adapter, client, mapping, config, errors
├─ api/               # INBOUND adapters: FastAPI routes + request/response schema
│   └─ routes.py, schemas.py              # (transport, NOT domain-typed raw)
└─ contracts/         # public bus events/commands for other slices (only import surface)
```

Shared (not per-slice): `app/infrastructure/{tooling,stores,buses,bridges,providers}` shared when genuinely reused (e.g., `stores/clickhouse` is one adapter used by many slices; outbox helper `stores/outbox`). Slices still declare their own *ports*; the shared store adapters simply implement them.

## 5. Integration boundary anatomy (each vendor = one boundary)

```
infrastructure/providers/exchange/binance/
├─ adapter.py     # implements marketdata.MarketDataSource (+ trading.OrderGateway)
│                 #   thin: composes client + mapping + tooling; returns domain models
├─ client.py      # SDK/API wrapper ONLY: raw HTTP/ccxt calls, pagination, auth signing
├─ dtos.py        # vendor-specific response models (SDK/JSON payloads) — never exported
├─ mapping.py     # normalize vendor DTO → domain models/events (G8); validate via pydantic
├─ config.py      # BinanceConfig: api_key, secret, base_url, limits, timeouts, retries
│                 #   (pydantic; secret fields redacted in logs)
├─ errors.py      # vendor exceptions → domain error mapping (rate-limit→RateLimitedError, …)
└─ tests.py       # port contract suite (must pass) + vcrpy cassettes + WireMock sourcing
```

Boundary responsibility checklist (each adapter): SDK-specific models · authentication/signing · configuration · rate limiting · retries+backoff · timeouts · circuit breaking · pagination · error mapping · idempotency (idempotency keys / event dedup) · serialization · vendor behaviour (timezone, precision, symbol formats, fee models, polling idioms).

## 6. Configuration strategy

```toml
[integrations.market_data]
provider = "binance"            # ← the ONLY knob to swap provider (G4)
paper    = true

[integrations.market_data.binance]
base_url = "https://api.binance.com"
api_key  = "${BINANCE_API_KEY}"
api_secret = "${BINANCE_API_SECRET}"     # secret; redacted everywhere
rate_limit_per_sec = 5
timeout_sec = 10
retries = 3
circuit_open_after = 5
backoff_base_sec = 0.5

[integrations.llm]
provider = "zen"                 # zen | openai | anthropic | local
base_url = "https://opencode.ai/zen/v1"
model = "nemotron-3-ultra-free"
api_key = "${OPENCODE_API_KEY}"
fallback = [{ provider = "local", model = "heuristic-v1" }]
```

- Each vendor config is **owned by its boundary** (pydantic model in `config.py`), registered in a `provider_registry` mapping `(capability, provider) → adapter factory`.
- DI reads `integrations.<capability>.provider` and hot-wires the matching factory. Environment variables via `${VAR}` resolve; secrets guarded.
- Adding a provider: new `<vendor>/` package + config block + registry entry. **No domain or application code changes.**

## 7. Cross-cutting infra toolkit (`app/infrastructure/tooling`)

Shared policies composed by adapters (G7) — infrastructure-side only:

- `Retryer` (fixed/exp backoff, jitter, max attempts, retryable-error policy)
- `CircuitBreaker` (failure threshold, open→half-open, per-capability keys)
- `RateLimiter` (token bucket/leaky bucket; Redis-backed optional)
- `Policy.run(fn)` composition helper (retry ⊗ breaker ⊗ timeout ⊗ ratelimit)
- `Paginator` (cursor/id/offset/page helpers for arbitrary vendor conventions)
- `ErrorMapper` (base mapper interface + helpers; each vendor supplies its own mapping table)
- `IdempotencyGuard` (derives/validates idempotency keys, dedup store—outbox/KV port)
- `Serde` (JSON/msgpack envelopes per provider DTO, date/tz normalisation)
- `Clock`, `SnowflakeId`/`Uuid`
- `HealthProbe` (shared health-check surface for adapters → composition root `/metrics` + `/health`)

These are infrastructure concerns; `domain`/`application` never import them.

## 8. Normalized models & events

Domain models are capability-defined (G2): `Symbol`, `Candle`, `Ticker`, `Balance`, `Position`, `Order`, `Fill`, `NewsArticle`, `SocialPost`, `SentimentScore`, `AnalysisResult`, `FeatureVector`, `PnlRecord`, `AlertMsg`, `ModelMetrics`. All Pydantic v2, timezone-UTC, numeric precision enforced.

Domain events (on bus, carrying normalized models): `CandleReceived`, `TickerUpdated`, `NewsIngested`, `SentimentComputed`, `SignalEmitted`, `DecisionMade`, `OrderSubmitted`, `OrderStateChanged`, `FillRecorded`, `PnlRecorded`, `ModelPromoted`, `RiskBreached`, `KillSwitchTriggered`. Event id (UUID) = dedup key (G6 idempotency).

## 9. Error-handling strategy

- **Domain error taxonomy** (in `core/exceptions`, used by use-cases; adapters map INTO it):
  `ProviderUnavailableError`, `RateLimitedError`, `AuthenticationError`, `ProviderValidationError`, `MalformedDataError`, `UnsupportedCapabilityError`, `TimeoutError`, `IdempotencyConflictError`, `ConfigurationError`, `RiskBlockError`, `FatalSystemError`.
- **Boundary rule:** `errors.py` of each vendor maps every provider/SDK exception into exactly one of the above — SDK exceptions NEVER cross the boundary (G1). Unknown errors map to `ProviderUnavailableError` + logged with correlation_id at WARN; no raw SDK types in domain logs/returns.
- `RecoverableError` vs `FatalSystemError` upstream decision drives retry/alerting policy.
- Retries distinguish safe-to-retry (`RateLimitedError`, `ProviderUnavailableError`) from unsafe (`ProviderValidationError`, idempotency conflicts).

## 10. DI & composition root

- **Composition root only:** `app/api/di.py` (FastAPI app), `app/workers/*.py`. Nowhere else constructs concrete adapters.
- `Container` (lightweight, testable — e.g., `punq` or hand-rolled registry): `register(ports.X, factory)` from config; **application/domain request ports; composition root provides implementations**.
- FastAPI lives only in `app/modules/*/api` (inbound adapters) — the framework never leaks into services.
- Tests construct the container with **in-memory/fake adapters** implementing the same ports.

## 11. Testing strategy

| Layer | Approach |
|---|---|
| Domain/application | pure unit tests; fakes satisfying ports (in-memory `CandleStore`, stub `LLMReasoner`) |
| Contract suites | **one suite per port** (e.g., `MarketDataSourceContractSuite`) run against EVERY adapter ↔ swap confidence (G4). Includes normalization, error mapping, idempotency, pagination cases |
| Adapter/boundary | integration tests vs sandbox APIs, `vcrpy` cassettes for determinism, `WireMock` for failure injection (500s, rate-limits, timeouts, partial payloads) |
| Data/store adapters | testcontainers (real ClickHouse/Postgres/Redis/Kafka) — compact contract suites per store port |
| Bus/outbox | real container tests: publish→consume, redelivery dedup, crash-in-middle recovery |
| Full slice | slice integration: fake-provider + real-store over bus |
| System | E2E (Playwright + API E2E) against deployed stack (Workers + VPS + DBs) |

**Swap test:** any adapter replacing another must pass the same port contract suite + recorded-cassette suite; documented difference sheet.

## 12. Adding / replacing a provider (operation)

1. Add `infrastructure/providers/<capability>/<vendor>/` package (boundary anatomy §5).
2. Implement the port(s) fully; run the port contract suite + boundary tests (cassettes/WireMock).
3. Add config block + `provider_registry` entry.
4. Flip `integrations.<capability>.provider` in env. Deploy. Rollback = flip back (previous image).
5. No domain/application/other-slice changes. Reviewed against §1 guarantees in CI (import-linter).

## 13. Guarantee matrix (examples)

| Replace | Touched files | Untouched |
|---|---|---|
| Binance → Kraken | `providers/exchange/kraken/*`, config | strategies, risk, llm, dashboard, domain |
| NewsAPI → RSS/GDELT | `providers/news/{rss,gdelt}/*`, config | sentiment app, domain |
| Zen → self-hosted LLM | `providers/llm/local/*`, config | decision fusion, domain |
| ClickHouse → Timescale | `stores/clickhouse(→timescale)*`, config | all slices (ports unchanged) |
| Redis Streams → Kafka | `buses/kafka/*`, config | all slices (EventBus port unchanged) |
| Slack → Telegram/webhook | `notify/*`, config | alert rules, risk |

---

Linked from: `docs/SYSTEM-DESIGN.md` · updated in `docs/SDLC-PLAN.md` sprint S1 · enforced by import-linter + port-contract suites in CI (`docs/DEVOPS-PLAN.md`, `docs/STLC-PLAN.md`).