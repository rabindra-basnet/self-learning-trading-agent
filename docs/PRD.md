# PRD -- Self-Improving AI Trading Agent

Status: DRAFT (approved v1) . Owner: product . Sources: SDLC-PLAN.md rev 3.1

---

## 1. Problem & Goal

A multi-asset (Crypto -> Stocks -> Forex) trading agent that **improves itself** via strategy optimization, ML retraining, LLM-powered analysis, and reinforcement learning -- while enforcing strict risk controls and running within a minimal-cost, serverless-friendly footprint (Cloudflare + Vercel edge, one minimal VPS for the engine).

## 2. Users & Roles

| Role | Needs |
|---|---|
| Admin/owner | configure strategies & risk, watch full P&L, kill-switch |
| Analyst | model/strategy performance, backtests, LLM analyses |
| Viewer | read-only dashboard, alert feed |

## 3. Feature Requirements (user stories + acceptance criteria)

### FR-1 LLM-Powered Analysis
- **As** the agent, **I** analyze market/news/sentiment via an OpenAI-compatible LLM gateway (default `https://opencode.ai/zen/v1`, free models) with configurable provider/model keys.
- **AC:** provider is config-driven; secrets in env never logged; API keys can be user-provided securely; on provider failure a fallback chain runs.

### FR-2 Strategy Optimization
- **AC:** nightly optimizer tunes strategy params on paper performance; results recorded (MLflow); promotion only after validation gate.

### FR-3 ML Retraining
- **AC:** scheduled retraining on new candles; walk-forward validated; regression guard (Sharpe/MDD) before promote.

### FR-4 Reinforcement Learning
- **AC:** a `gymnasium` environment wraps the paper engine; learned policies are challengers; promotion gate identical.

### FR-5 Risk Management (all profiles)
- **AC:** conservative / aggressive / configurable profiles; per-trade stop-loss, max daily loss, drawdown circuit breaker, static kill-switch; **order executor is fail-closed on risk**.

### FR-6 Pluggable Data Providers (loosely coupled)
- **AC:** exchange/news/social/alt-data behind Strategy+Adapter+Factory; adding a new provider = new adapter only; no domain changes.

### FR-7 Real-Time Dashboard (unified web app)
- **AC:** live equity/P&L, positions/trades table, model & strategy performance, risk panel + kill-switch, alert feed; updates over WebSocket from engine.

### FR-8 Production-Grade QA
- **AC:** integration-first + E2E-first suites (§STLC) gated in CI/CD.

## 4. Data Contracts (v1)

`Ticker . Candle . NewsItem . SentimentScore . Signal . Decision . Order . Fill . PnlRecord . ModelMetrics . StrategyParams . RiskProfile . PortfolioSummary`

Owned in `app/modules/<slice>/contracts/`; OpenAPI published for `web/`.

## 5. Non-Functional Requirements

| NFR | Target |
|---|---|
| Performance | ingest >= 1 msg/s/symbol; API p95 < 300 ms; WS p95 < 150 ms |
| Availability | engine SLO 99.5%; 0 silent order failures |
| Security | secrets never logged; JWT RBAC; fail-closed risk; OWASP-clean |
| Scalability | slices extractable to services without domain rewrite (outbox est.) |
| Cost | minimal VPS (1 vCPU) + CF/Vercel free tiers at launch |
| Observability | structured logs, metrics, traces, dashboards |
| Testability | integration-first + E2E-first test gates (§STLC) |

## 6. Out of Scope (v1)

Live real-money trading default (paper-first with gated unlock), options/shorting complexity, ultra-low-latency HFT, multi-user tenancy.