# System Design Document

Status: DRAFT (approved v1, VSA + unified web) · Source: SDLC-PLAN.md §2

---

## 1. Context

Single team, minimal infrastructure. Engine must run persistently → one minimal VPS (Docker); the single unified Next.js 16 `web/` app (dashboard + API edge + LLM proxy) deploys to Cloudflare Workers primarily and to Vercel as an unchanged fallback. Cloudflare provides DNS/CDN/WAF/rate-limiting.

## 2. Architecture Axioms

1. **Vertical slices, not layers.** Every capability is self-contained (`api/application/domain/infrastructure/contracts`).
2. **Strict dependency rule:** slices depend on `core/` and on `contracts/` of other slices only. Enforced by `import-linter` in CI (no runtime coupling).
3. **Schema-per-context:** Postgres schema per slice + ClickHouse DB per slice; separate DB users (defense-in-depth).
4. **Events over calls across slices:** outbox → Redis Streams; consumers idempotent.
5. **Anti-corruption at the edge:** every external provider hidden behind an adapter in the owning slice's `infrastructure/`.
6. **Fail-closed risk:** the trading gate blocks any order unless risk validated.
7. **Composition root** in `app/api` and `app/workers` wires all DI/connections.

## 3. System Diagram

```
 Data (exchange/news/social/alt)                    UI browser
        │                                               │
        ▼                                               ▼
┌────────────────────────┐                       Cloudflare (DNS/CDN/WAF)
│  SLICES (Python engine)│                       ┌──────────────────────┐
│  marketdata · signals  │      REST/WS          │  web/ Next.js 16     │
│  sentiment · strategies│◀─────────────────────▶│  dashboard + API     │
│  risk · trading · llm  │                       │  routes + middleware │
│  selfimprovement       │                       │  + LLM proxy -> Zen  │
│  history · dashboard   │                       └──────────────────────┘
│  auth · alerts         │   reads                 (Vercel fallback)
└──────────┬─────────────┘
           │ outbox / event bus (Redis Streams)
           ▼
┌─────────────────────────────┐
│  PostgreSQL (txns/slices)   │
│  ClickHouse (analytics)     │
│  Redis (cache/WS fanout/q)  │
└─────────────────────────────┘
```

## 4. VSA Details

> **Integration isolation is governed by `docs/INTEGRATION-ARCHITECTURE.md` (Ports & Adapters / Hexagonal) and enforced in CI.** The rules below are the hexagonal slice shape; the port/adapters catalogue, boundary anatomy, DI, config, and test strategy live in that document.

Package layout:

```
app/
├─ core/  config · logging · exceptions · auth · db · messaging(openbox) · observability · common(Result[T,E], feature-flags, pagination)
├─ modules/<slice>/{domain,application,infrastructure,api,contracts}/
├─ infrastructure/  shared stores/buses/bridges/tooling (adapters)
├─ api/   main.py · routers.py · di.py      # composition root
└─ workers/  (APScheduler/Celery queue + scheduled entrypoints)
```

Slice internals (hexagonal):

| layer | responsibility | may import |
|---|---|---|
| `domain/` | entities, value objects, invariants/policies, **ports (capability interfaces)**, domain events | core pure types only — **zero provider/infra imports** |
| `application/` | use-cases; depend only on ports | domain, core |
| `infrastructure/` | OUTBOUND adapters implementing ports + shared store/bus/bridge/tooling | domain ports, core tooling |
| `api/` | INBOUND adapters: routers, request/response schemas | application |
| `contracts/` | PUBLIC bus events/commands only — the single import surface for other slices | core |

## 5. Message Contracts (bus)

- Events: `CandleReceived`, `TickerUpdate`, `NewsIngested`, `SentimentComputed`, `SignalEmitted`, `DecisionMade`, `OrderStateChanged`, `FillRecorded`, `PnlRecorded`, `ModelPromoted`, `RiskBreached`, `KillSwitchTriggered`.
- Consumed per slice via consumer groups (Redis Streams `XADD`/`XREADGROUP`).
- Outbox table per slice (`<slice>.outbox`) fanned out within the producing transaction.

## 6. Domain highlights

- **OrderStateMachine:** `NEW → SUBMITTED → PARTIALLY_FILLED → FILLED | CANCELED | REJECTED | EXPIRED`; illegal transitions raise `InvalidOrderTransition`.
- **RiskManager (fail-closed):** `check(decision) → Ok | RiskBlock(reason)`. Profiles: conservative / aggressive / custom; limits: per-trade stop-loss, max daily loss, max drawdown, exposure caps, position sizing.
- **Champion/Challenger:** `model_registry` holds champion + challengers; promotion requires held-out walk-forward beat + paper shadow ≥ 14 days (seed-locked, signed, reverted-able).

## 7. Databases

### 7.1 PostgreSQL (per-context schemas)
`auth`: users, api_keys(hashed) · `trading`: orders, positions, fills · `strategies`: strategies, strategy_params, experiments · `risk`: risk_profiles, breach_events, kill_switch · `model_registry`: models, promotions, rollbacks · `alerts`: alert_rules, alert_events

### 7.2 ClickHouse (MergeTree, per-context DBs)
`marketdata`: market_candles, market_trades · `signals`: feature_snapshots · `history`: equity_curve, trade_pnl (+monthly materialized views) · `llm`: llm_analyses(JSON), sentiment_scores · `models`: model_predictions, model_performance(mv)

### 7.3 Redis
cache keys, streams (outbox fanout), rate-limit counters, WS fanout lists, job queue.

## 8. APIs

- **Engine (FastAPI, mounted under `/api/v1`):** modules' routers mounted in composition root; JWT auth; OpenAPI served.
- **WebSocket `/ws/live`:** authenticated; pushes equity, positions, model perf, alerts, health (projections from `history`/`dashboard`).
- **`web/` Route Handlers:** `auth`, `trades`, `positions`, `live`, `models`, `risk` (thin proxy) + `llm` (server-side Zen proxy). Edge `middleware.ts`: JWT verify + basic rate-limit; heavy rate-limit at CF WAF.

## 9. LLM integration

- Provider adapters (`OpenAICompatibleProvider`) behind Factory; config: base_url, model id, api_key source (env/secret), fallback chain (e.g. free→fallback→local heuristic), `max_tokens`, `temperature`, timeouts, retry policy.
- Prompt templates versioned; outputs Pydantic-validated (`AnalysisResult`/`SentimentScore`); **tokens/cost + latency recorded to ClickHouse**.
- Default gateway `https://opencode.ai/zen/v1` (chat/completions or responses per model).

## 10. Security (see SECURITY.md)

JWT(short) + refresh + RBAC · risk fail-closed · secrets never logged · CF WAF · Pydantic validation · SAST/DAST/SCA/gitleaks in CI.

## 11. Observability

- structlog JSON + `correlation_id` (trace injection); exception middleware → normalized envelope.
- Prometheus metrics: trades, pnl, mm/latency, llm cost/latency, queue depth, db latency, risk blocks; `/metrics`.
- OTel traces → Tempo/Zipkin; Loki log aggregation.
- Error taxonomy: `RecoverableError`, `ProviderUnavailableError`, `ConfigValidationError`, `RiskBlockError`, `FatalSystemError`.

## 12. Deployment Topology

```
BROWSER → CF (DNS/CDN/WAF)
   ├─ web/ (Next 16) → Cloudflare Workers (OpenNext)      [primary]
   │                          ↕ same package also Vercel   [fallback]
   └─ engine (FastAPI/WS) → VPS Docker (engine,workers,pgsql,clickhouse,redis,proxy)
```

Secrets on CF via `wrangler secret put`; Vercel env fallback; VPS via env + optional SOPS. Incremental cache bound to KV (or R2). Images via CF Images binding. No request-time FS reads.

## 13. ADRs (to be authored in Phase 2)

Event bus Redis-Streams vs Kafka · broker lib ccxt · ORM SQLAlchemy-2-async vs raw · ML: PyTorch vs LightGBM for forecasts · RL: stable-baselines3 + gymnasium env · scheduler APScheduler vs Celery · observability OTel vs vendor · monolith-first extraction strategy.