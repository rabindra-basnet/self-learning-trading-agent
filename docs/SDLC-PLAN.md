# SDLC Master Plan â€” Self-Improving AI Trading Agent

- **Status:** APPROVED (rev. 3 â€” VSA + unified Next.js 16 `web/`)
- **Gate rule:** No business code before Phase 3 â€” S0/S1/S2 produce artifacts only.

---

## 0. Deployment Reality Check (verified, 2026)

| Platform | Can host the Python engine? | Reality |
|---|---|---|
| Vercel | No | `Dockerfile.vercel` = Fluid compute: scale-to-zero, **30 s SIGTERM** on idle, **no WebSockets**, **no persistent disk**, Pro-only. OK for dashboard/web. |
| Cloudflare Workers | No | Python via **Pyodide (WASM)** â€” no long-running processes, no durable sockets. |
| Cloudflare Containers | Paid | GA Apr 2026; any Dockerfile at edge, billed per use. Fallback option. |
| Minimal VPS / Fly.io / Railway free tier | **Yes â€” primary** | Needs 24/7 uptime, WebSockets, disk, long-running RL training. |

**Target topology**

```
BROWSER
   â”‚
   â–¼
Cloudflare (DNS Â· CDN Â· WAF Â· DDoS Â· rate-limit)
   â”‚
   â”œâ”€â”€â–¶ web/  Next.js 16 (Workers Assets + Route Handlers + Edge middleware)  [PRIMARY]
   â”‚         â€¦same package also deployable to Vercel unchanged                [FALLBACK]
   â”‚
   â””â”€â”€â–¶ [Minimal VPS]  Docker  â”€â”€â–¶ Python Trading Engine (FastAPI, WS, workers)
         â”œâ”€ PostgreSQL      â”œâ”€ ClickHouse      â””â”€ Redis
```

**Why:** neither Cloudflare nor Vercel can run long-lived Python processes on a free tier. Cloudflare and Vercel host the single unified web app (edge + UI); a minimal VPS runs the always-on Python engine.

---

## 1. Requirements Summary

1. **LLM-Powered Analysis** â€” OpenAI-compatible; default `https://opencode.ai/zen/v1` with free models (`nemotron-3-ultra-free`, `big-pickle`, â€¦); provider/model configurable per user with **secrets never logged**; user-supplied provider keys supported.
2. **Strategy Optimization** â€” auto-tune strategy parameters on live performance.
3. **ML Model Retraining** â€” automatic retrain on new market data.
4. **Reinforcement Learning** â€” reward-driven action learning (`gymnasium` env on paper engine).
5. **All risk profiles** â€” conservative / aggressive / configurable + hard circuit breakers.
6. **Loosely-coupled providers** â€” exchange / news / social / alt-data are pluggable (Strategy+Adapter+Factory). Best-practice OOP + design patterns, no over-engineering.
7. **Enterprise-grade logging & error/exception handling** â€” structured logs, error taxonomy, correlation IDs, alerting, fail-closed risk.
8. **Persistent + Timeseries DB** â€” PostgreSQL (transactions) + ClickHouse (analytics).
9. **Real-time dashboard** â€” P&L, trades, model performance, strategy health, system health.
10. **Production-grade testing** â€” **Integration-first and E2E-first** STLC (see Â§4).

**Multi-asset:** Crypto (Binance) â†’ Stocks (Alpaca) â†’ Forex (OANDA) in that build order; adapter architecture makes later providers trivial.

---

## 2. System Design (see docs/SYSTEM-DESIGN.md for the full document)

### 2.0 Monorepo

```
/D:
â”œâ”€ app/           # Python trading engine â€” VSA modular monolith
â”œâ”€ web/           # SINGLE Next.js 16 app = dashboard + API edge + LLM proxy
â”œâ”€ docs/          # PRD, SDLC, STLC, DEVOPS, SYSTEM-DESIGN, SECURITY, CONVENTIONS
â”œâ”€ infra/         # Terraform, docker-compose, GitHub Actions, runbooks
â””â”€ pnpm-workspace.yaml   # one command starts the web app locally
```

### 2.1 Vertical Slice Architecture (VSA / modular monolith)

Each business capability = **one vertical slice**, fully self-contained: `api / application / domain / infrastructure / contracts`. Slices communicate only via **typed contracts** (domain events / commands) through the shared bus â€” never each other's internals.

```
COMPOSITION ROOT  app/api (FastAPI) + app/workers
        â”‚
SHARED KERNEL  core/  Â· config Â· logging Â· exceptions Â· auth Â· db Â·
                     Â· messaging(bus+outbox) Â· observability Â· common(Result[T,E])
        â”‚
SLICES  marketdata Â· signals Â· sentiment Â· strategies Â· risk Â· trading Â·
        llm Â· selfimprovement Â· history Â· dashboard(read) Â· auth Â· alerts
```

**Enforcement (keeps it managed & scalable)**
1. Slices depend on `core/` + `contracts/` only. `import-linter` (CI) blocks sliceâ†’slice internal imports.
2. **Schema-per-context**: each slice owns its Postgres schema + ClickHouse DB; separate DB users per context.
3. **Outbox pattern**: domain events fanned out atomically with the producing DB transaction â†’ Redis Streams consumer groups â†’ any slice can graduate to a service later without rewrites.
4. **CQRS-lite**: writes via commands; dashboard/analytics read from ClickHouse projections.

### 2.2 Slice ownership map

| Slice | Owns |
|---|---|
| `marketdata` | candle/ticker ingest, exchange adapters, market tables |
| `signals` | indicators, feature pipeline |
| `sentiment` | news/social adapters, sentiment scores |
| `strategies` | strategy defs, params, backtest harness |
| `risk` | risk profiles, circuit breakers, kill-switch (fail-closed gate) |
| `trading` | orders, positions, order-state machine, executor, PnL events |
| `llm` | LLM provider abstraction (Zen default), analysis, decision fusion |
| `selfimprovement` | reward, optimizer, retrain, RL, champion/challenger, model registry |
| `history` | equity curve & PnL analytics read-model |
| `dashboard` | aggregation read-models + WS projections for `web/` |
| `auth` | JWT, RBAC, api_keys (hashed) |
| `alerts` | alert rules, Slack/Telegram/webhook dispatch |

### 2.3 Communication & reliability (futuristic defaults)

- `Result[T, E]` returns + typed error taxonomy (no try/except soup). Correlation ID threads through every call.
- **Outbox** â†’ at-least-once delivery, idempotent consumers (dedup by event id).
- **Anti-corruption layer** at every external provider; domain never sees vendor types.
- **Bulkhead + Circuit breaker** per slice resource; failover chains (e.g. LLM â†’ fallback model â†’ local heuristic).
- **Feature flags + gradual rollout**; champion/challenger strategies ship behind flags.
- **Extraction-ready**: monolith-first; events can always be "exported" later.
- **Composition root** only wires DI / connections / queues â€” no hidden singletons.

### 2.4 Package layout (Python `app/`)

```
app/
â”œâ”€ core/                  # shared kernel (slices may NOT import app.modules.*)
â”œâ”€ modules/
â”‚  â”œâ”€ <slice>/  {api, application, domain, infrastructure, contracts}/
â”œâ”€ api/                   # composition root: main.py, routers.py, di.py
â””â”€ workers/               # queue/scheduler entrypoints
```

Architecture tests in CI: `coreâ‡¢nothing; slicesâ‡¢core âœ“; slicesâ‡¢slices âœ— (contracts only); modulesâ‡¢api âœ—`

### 2.5 Unified `web/` (single Next.js 16 app)

```
web/  (Next.js 16 Â· App Router Â· React 19 Â· TS Â· Tailwind 4)
â”œâ”€ app/
â”‚  â”œâ”€ (dashboard)/        # UI panels
â”‚  â”œâ”€ api/                # ROUTE HANDLERS = the edge/API layer
â”‚  â”‚  â”œâ”€ trades/route.ts  # thin proxy â†’ Python engine
â”‚  â”‚  â”œâ”€ live/route.ts    # health/live forward
â”‚  â”‚  â”œâ”€ llm/route.ts     # LLM proxy (opencode.ai/zen) â€” server-side keys only
â”‚  â”‚  â””â”€ auth/route.ts    # JWT issue/refresh
â”‚  â”œâ”€ middleware.ts       # EDGE middleware: JWT verify, basic rate-limit
â”‚  â””â”€ â€¦
â”œâ”€ lib/  components/  open-next.config.ts  wrangler.jsonc  next.config.ts
```

- **One instance, started together:** local `pnpm dev` runs the whole web app while `docker compose up` runs the engine.
- **Primary deploy:** `opennextjs-cloudflare build && deploy` â†’ UI + API edge deploy to Cloudflare Workers as one unit.
- **Fallback deploy:** the same package deploys to Vercel unchanged. No separate Hono worker.
- Edge constraints honored: Edge-safe `middleware.ts` (Next 16 `proxy.ts` is Node-only, unsupported on CF), heavy rate-limit via CF WAF, no request-time filesystem reads, KV incremental cache, CF Images, WS owned by the Python engine (`web/` is the WS client).

### 2.6 Databases

- **PostgreSQL:** users, api_keys(hashed), portfolios, orders, positions, strategies, strategy_params, risk_profiles, alerts, model_registry, experiments
- **ClickHouse (MergeTree):** market_candles, market_trades, feature_snapshots, llm_analyses(JSON), sentiment_scores, model_predictions, model_performance(+materialized views), trade_pnl, equity_curve
- **Redis:** cache, event bus streams, rate-limit, WS fan-out, job queue

### 2.7 Security (see docs/SECURITY.md)

- Secrets in env/secret-manager; **never logged or committed**; LLM keys used server-side in `web/api/llm` or engine.
- JWT (short-lived) + refresh; RBAC viewer/analyst/admin.
- CF WAF + rate-limit on edge; Cloudflare DNS/CDN in front.
- **Risk gate is fail-closed**: executor cannot trade without risk sign-off. Paper-trade default.
- AppSec: Pydantic v2 validation, SAST/DAST/SCA + gitleaks in CI.

### 2.8 Observability

- Structured JSON logs (`structlog`) + `correlation_id`.
- Error taxonomy: `RecoverableError`, `ProviderUnavailableError`, `ConfigValidationError`, `RiskBlockError`, `FatalSystemError`.
- Unhandled-exception hooks â†’ normalized envelope + metric increment.
- Prometheus `/metrics` + Grafana; OTel traces â†’ Tempo/Zipkin; Loki logs.

---

## 3. SDLC Phases (gates)

| Phase | Deliverable | Gate |
|---|---|---|
| 0 Planning | This doc + docs/* | Sign-off |
| 1 Requirements | PRD, user stories, AC, data contracts | Sign-off |
| 2 System Design | ADRs, schemas, OpenAPI, WS contract, ML design, threat model | Sign-off |
| 3 Development | Sprint S0â€“S8 (below), TDD throughout | Green CI + coverage |
| 4 Code Review | Pre-commit (ruff/mypy/bandit/semgrep), ADR conformance | Approval to test |
| 5 Test (STLC) | See docs/STLC-PLAN.md | Green gates |
| 6 DevOps | See docs/DEVOPS-PLAN.md | Deployed |
| 7 Ops | SLOs, runbooks, self-improvement tuning | Ongoing |

**Sprints (vertical, feature-first)**

| Sprint | Delivers (usable, tested slices) |
|---|---|
| S0 | Repo init (this) + core kernel skeleton + arch constraints |
| S1 | `auth` + `marketdata` end-to-end |
| S2 | `signals` + `strategies` + backtest; `risk` fail-closed gate |
| S3 | `trading` (paper executor) + `sentiment` |
| S4 | `llm` (Zen) + decision fusion |
| S5 | `selfimprovement` (optimizer/retrain/RL/champion-challenger) |
| S6 | `history` + read-API/WS + **`web/` first bed** (single app) |
| S7 | `web/` LLM proxy + full dashboard + CF deploy + Vercel portability |
| S8 | Hardening: chaos/load/security, runbooks, regression, docs |

---

## 4. STLC / QA â€” Integration-first, E2E-first

**Testing emphasis (per product decision): Integration and E2E testing are first-class; unit tests cover only pure core logic.**

Target mix: **Integration ~45% Â· E2E ~35% Â· Unit ~20%**

| # | Level | Tools | Scope |
|---|---|---|---|
| T1 | Test planning | Strategy doc, traceability matrix | Every req â†’ â‰¥1 test |
| T2 | Test design | Gherkin `.feature` | buy/hold/sell/risk-blowup |
| T3 | **Integration** | pytest + **testcontainers** (real PG/ClickHouse/Redis) + **vcrpy** replay + WireMock | adapterâ†”bus, repoâ†”DB, sliceâ†”slice over real infra; provider failures, outbox delivery |
| T4 | **E2E** | **Playwright** (web) + **API E2E** against a deployed env (Workers + VPS + DBs) | full order flow, LLM proxy, WS updates, risk kill-switch, strategy promotion |
| T5 | Contract | pact-like between `web/` and engine API; slice contracts | schema drift prevention (OpenAPI) |
| T6 | Backtest regression | walk-forward, seed-locked | retraining doesn't regress Sharpe/MDD |
| T7 | Load/Perf | Locust + k6 | peak ticks, 10k WS conns, API p95 |
| T8 | Chaos | fault injection (kill Redis/drop exchange/LLM 500/suspend net) | self-heal/failover/graceful |
| T9 | Security | OWASP ZAP, Bandit/Semgrep, pip-audit, gitleaks | auth bypass, injection, secrets |
| T10 | UAT/demo | graded scenario walkthrough | stakeholder sign-off |
| T11 | Regression | per-PR smoke integration-E2E; nightly full suite | no escapes |

**Gates**
- Every PR: lint+type + unit + **integration suite (minimal subset, real containers)** + smoke E2E on preview env.
- Every release candidate: **full integration suite + full E2E (Playwright + API E2E) against staging deployed stack**; chaos + load + security in RC hardening.
- Long-runner rule: **no order is ever sent to live market during CI** â€” paper/`live-simulated` only.

---

## 5. DevOps (see docs/DEVOPS-PLAN.md)

Git (trunk+short branches, Conventional Commits) Â· GitHub Actions CI (`lint â†’ mypy â†’ unit â†’ integration(testcontainers) â†’ coverage â‰¥85% â†’ SAST â†’ E2E(playwright, preview) â†’ build image`) Â· CD: VPS watchtower blue-green, `wrangler deploy` for web, Vercel fallback Â· Terraform (DNS/Workers/R2) Â· docker-compose for VPS Â· envs: dev â†’ staging(paper) â†’ prod(gated) Â· pydantic-settings + SOPS/age + .env.example Â· backups PGâ†’R2, ClickHouseâ†’R2 daily Â· SLOs 99.5% engine, p95 API<300ms, p95 WS<150ms, 0 silent order failures Â· runbooks (incident, kill-switch, exchange/LLM outage, drift).

---

## 6. Self-Improvement Loop

```
Performance Logs â†’ 1. Score/cohort â†’ 2. Optimizer (grid/GA) â†’ 3. Retrain ML
                 â†’ 4. RL reward-walk â†’ 5. LLM meta-analysis â†’ 6. Walk-forward
                 validation (held-out) + paper shadow A/B â‰¥14d â†’ promote
                 champion or revert (rolled-back via model_registry)
```

**Guardrails:** champion/challenger; challenger goes live only if it beats champion on held-out + paper shadow; every change recorded & rollbackable; **self-improvement can never override the risk manager.**

---

## 7. Tech Stack

**Python engine (3.12):** FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, clickhouse-connect, redis, ccxt, pandas/numpy, openai (base_url=Zen), structlog, OTel, prometheus-client, APScheduler/Celery, scikit-learn, PyTorch, stable-baselines3, gymnasium, MLflow.
**Web (single package):** Next.js **16**, React 19, TS, Tailwind 4, Tremor, Recharts, TanStack Query, Zustand, `@opennextjs/cloudflare`, wrangler; Vercel-portable.
**Edge:** Next.js Route Handlers + Edge `middleware.ts` (no separate Hono worker).
**Infra/Obs:** Docker, docker-compose, Terraform, GitHub Actions, Prometheus, Grafana, Loki, Tempo/Zipkin.

---

## 8. Execution Prompts (after sign-off)

1. **P0 â€” Repo init:** create repo skeleton per Â§2 (dirs, docs filled from plan, AGENTS.md, .editorconfig, .gitignore, pre-commit, Conventional Commits, import-linter constraints). No business logic.
2. **P1 â€” Foundations:** Python package: pydantic-settings config + .env.example, structlog with correlation_id, domain models + `Result[T,E]` + exception taxonomy, repository interfaces. Unit tests for order-state machine & position math. Gates: mypy+ruff clean, coverage â‰¥85%.
3. **P2 â€” Data layer:** Postgres migrations (Alembic, schema-per-context), ClickHouse DDL + writer, Redis + outbox event bus. Integration tests with testcontainers.
4. **P3 â€” Ingestion:** `marketdata` + `sentiment` adapters (ccxt Binance, NewsAPI, Reddit) via Factory registry; CircuitBreaker + structured logging. **Integration tests (vcrpy real-recorded fixtures) + contract tests.**
5. **P4 â€” Strategies & Execution:** Strategy framework + backtest harness (walk-forward); `risk` fail-closed gate; `trading` paper executor + state machine. Integration tests of riskâ†’executor chain; seeded backtest gates.
6. **P5 â€” LLM layer:** LLM Provider abstraction (Zen default + fallback chain), sentiment consumer, decision fusion. Integration tests with mocked + recorded provider responses and failover verification.
7. **P6 â€” Self-improvement loop:** rewardâ†’optimizerâ†’retrainâ†’RL; champion/challenger + promotion gate with walk-forward; MLflow-recorder. Backtest-regression + E2E promotion scenario (paper).
8. **P7 â€” Unified web app:** Next.js 16 `web/` â€” dashboard, Route Handlers (auth/trades/live/llm proxyâ†’Zen), Edge middleware; `@opennextjs/cloudflare` deploy + Vercel portability check. **E2E with Playwright against deployed Workers; API E2E against deployed stack.**
9. **P8 â€” DevOps/QA hardening:** GitHub Actions CI/CD per Â§5; Terraform; chaos + load + security audits; runbooks + Grafana/Loki; **full integration + E2E regression** for the release candidate.

---

## 9. Approval Log

| Rev | Change | Approved |
|---|---|---|
| 1 | Baseline plan (SDLC/STLC/QA/DevOps/System Design) | â€” |
| 2 | Vertical Slice Architecture (VSA), schema-per-context, outbox, import-linter | â€” |
| 3 | Unified single Next.js 16 `web/` (dashboard + edge), CF Workers primary / Vercel fallback | Approved |
| 3.1 | STLC emphasis: **Integration-first, E2E-first** (45/35/20) | Approved |