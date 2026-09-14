# System Design Document

Status: DRAFT (approved v1, VSA + unified web) Â· Source: SDLC-PLAN.md Â§2

---

## 1. Context

Single team, minimal infrastructure. Engine must run persistently â†’ one minimal VPS (Docker); the single unified Next.js 16 `web/` app (dashboard + API edge + LLM proxy) deploys to Cloudflare Workers primarily and to Vercel as an unchanged fallback. Cloudflare provides DNS/CDN/WAF/rate-limiting.

## 2. Architecture Axioms

1. **Vertical slices, not layers.** Every capability is self-contained (`api/application/domain/infrastructure/contracts`).
2. **Strict dependency rule:** slices depend on `core/` and on `contracts/` of other slices only. Enforced by `import-linter` in CI (no runtime coupling).
3. **Schema-per-context:** Postgres schema per slice + ClickHouse DB per slice; separate DB users (defense-in-depth).
4. **Events over calls across slices:** outbox â†’ Redis Streams; consumers idempotent.
5. **Anti-corruption at the edge:** every external provider hidden behind an adapter in the owning slice's `infrastructure/`.
6. **Fail-closed risk:** the trading gate blocks any order unless risk validated.
7. **Composition root** in `app/api` and `app/workers` wires all DI/connections.

## 3. System Diagram

```
 Data (exchange/news/social/alt)                    UI browser
        â”‚                                               â”‚
        â–¼                                               â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                       Cloudflare (DNS/CDN/WAF)
â”‚  SLICES (Python engine)â”‚                       â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  marketdata Â· signals  â”‚      REST/WS          â”‚  web/ Next.js 16     â”‚
â”‚  sentiment Â· strategiesâ”‚â—€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¶â”‚  dashboard + API     â”‚
â”‚  risk Â· trading Â· llm  â”‚                       â”‚  routes + middleware â”‚
â”‚  selfimprovement       â”‚                       â”‚  + LLM proxy -> Zen  â”‚
â”‚  history Â· dashboard   â”‚                       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
â”‚  auth Â· alerts         â”‚   reads                 (Vercel fallback)
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
           â”‚ outbox / event bus (Redis Streams)
           â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  PostgreSQL (txns/slices)   â”‚
â”‚  ClickHouse (analytics)     â”‚
â”‚  Redis (cache/WS fanout/q)  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## 4. VSA Details

> **Integration isolation is governed by `docs/INTEGRATION-ARCHITECTURE.md` (Ports & Adapters / Hexagonal) and enforced in CI.** The rules below are the hexagonal slice shape; the port/adapters catalogue, boundary anatomy, DI, config, and test strategy live in that document.

Package layout:

```
app/
â”œâ”€ core/  config Â· logging Â· exceptions Â· auth Â· db Â· messaging(openbox) Â· observability Â· common(Result[T,E], feature-flags, pagination)
â”œâ”€ modules/<slice>/{domain,application,infrastructure,api,contracts}/
â”œâ”€ infrastructure/  shared stores/buses/bridges/tooling (adapters)
â”œâ”€ api/   main.py Â· routers.py Â· di.py      # composition root
â””â”€ workers/  (APScheduler/Celery queue + scheduled entrypoints)
```

Slice internals (hexagonal):

| layer | responsibility | may import |
|---|---|---|
| `domain/` | entities, value objects, invariants/policies, **ports (capability interfaces)**, domain events | core pure types only â€” **zero provider/infra imports** |
| `application/` | use-cases; depend only on ports | domain, core |
| `infrastructure/` | OUTBOUND adapters implementing ports + shared store/bus/bridge/tooling | domain ports, core tooling |
| `api/` | INBOUND adapters: routers, request/response schemas | application |
| `contracts/` | PUBLIC bus events/commands only â€” the single import surface for other slices | core |

## 5. Message Contracts (bus)

- Events: `CandleReceived`, `TickerUpdate`, `NewsIngested`, `SentimentComputed`, `SignalEmitted`, `DecisionMade`, `OrderStateChanged`, `FillRecorded`, `PnlRecorded`, `ModelPromoted`, `RiskBreached`, `KillSwitchTriggered`.
- Consumed per slice via consumer groups (Redis Streams `XADD`/`XREADGROUP`).
- Outbox table per slice (`<slice>.outbox`) fanned out within the producing transaction.

## 6. Domain highlights

- **OrderStateMachine:** `NEW â†’ SUBMITTED â†’ PARTIALLY_FILLED â†’ FILLED | CANCELED | REJECTED | EXPIRED`; illegal transitions raise `InvalidOrderTransition`.
- **RiskManager (fail-closed):** `check(decision) â†’ Ok | RiskBlock(reason)`. Profiles: conservative / aggressive / custom; limits: per-trade stop-loss, max daily loss, max drawdown, exposure caps, position sizing.
- **Champion/Challenger:** `model_registry` holds champion + challengers; promotion requires held-out walk-forward beat + paper shadow â‰¥ 14 days (seed-locked, signed, reverted-able).

## 7. Databases

### 7.1 PostgreSQL (per-context schemas)
`auth`: users, api_keys(hashed) Â· `trading`: orders, positions, fills Â· `strategies`: strategies, strategy_params, experiments Â· `risk`: risk_profiles, breach_events, kill_switch Â· `model_registry`: models, promotions, rollbacks Â· `alerts`: alert_rules, alert_events

### 7.2 ClickHouse (MergeTree, per-context DBs)
`marketdata`: market_candles, market_trades Â· `signals`: feature_snapshots Â· `history`: equity_curve, trade_pnl (+monthly materialized views) Â· `llm`: llm_analyses(JSON), sentiment_scores Â· `models`: model_predictions, model_performance(mv)

### 7.3 Redis
cache keys, streams (outbox fanout), rate-limit counters, WS fanout lists, job queue.

## 8. APIs

- **Engine (FastAPI, mounted under `/api/v1`):** modules' routers mounted in composition root; JWT auth; OpenAPI served.
- **WebSocket `/ws/live`:** authenticated; pushes equity, positions, model perf, alerts, health (projections from `history`/`dashboard`).
- **`web/` Route Handlers:** `auth`, `trades`, `positions`, `live`, `models`, `risk` (thin proxy) + `llm` (server-side Zen proxy). Edge `middleware.ts`: JWT verify + basic rate-limit; heavy rate-limit at CF WAF.

## 9. LLM integration

- Provider adapters (`OpenAICompatibleProvider`) behind Factory; config: base_url, model id, api_key source (env/secret), fallback chain (e.g. freeâ†’fallbackâ†’local heuristic), `max_tokens`, `temperature`, timeouts, retry policy.
- Prompt templates versioned; outputs Pydantic-validated (`AnalysisResult`/`SentimentScore`); **tokens/cost + latency recorded to ClickHouse**.
- Default gateway `https://opencode.ai/zen/v1` (chat/completions or responses per model).

## 10. Security (see SECURITY.md)

JWT(short) + refresh + RBAC Â· risk fail-closed Â· secrets never logged Â· CF WAF Â· Pydantic validation Â· SAST/DAST/SCA/gitleaks in CI.

## 11. Observability

- structlog JSON + `correlation_id` (trace injection); exception middleware â†’ normalized envelope.
- Prometheus metrics: trades, pnl, mm/latency, llm cost/latency, queue depth, db latency, risk blocks; `/metrics`.
- OTel traces â†’ Tempo/Zipkin; Loki log aggregation.
- Error taxonomy: `RecoverableError`, `ProviderUnavailableError`, `ConfigValidationError`, `RiskBlockError`, `FatalSystemError`.

## 12. Deployment Topology

```
BROWSER â†’ CF (DNS/CDN/WAF)
   â”œâ”€ web/ (Next 16) â†’ Cloudflare Workers (OpenNext)      [primary]
   â”‚                          â†• same package also Vercel   [fallback]
   â””â”€ engine (FastAPI/WS) â†’ VPS Docker (engine,workers,pgsql,clickhouse,redis,proxy)
```

Secrets on CF via `wrangler secret put`; Vercel env fallback; VPS via env + optional SOPS. Incremental cache bound to KV (or R2). Images via CF Images binding. No request-time FS reads.

## 13. ADRs (to be authored in Phase 2)

Event bus Redis-Streams vs Kafka Â· broker lib ccxt Â· ORM SQLAlchemy-2-async vs raw Â· ML: PyTorch vs LightGBM for forecasts Â· RL: stable-baselines3 + gymnasium env Â· scheduler APScheduler vs Celery Â· observability OTel vs vendor Â· monolith-first extraction strategy.