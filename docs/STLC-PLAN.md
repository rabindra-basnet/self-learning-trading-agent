# STLC Plan -- Integration-First & E2E-First

Status: DRAFT . Part of SDLC-PLAN.md §4

---

## 1. Principle

**Integration and E2E testing are first-class citizens.** Unit tests exist but are intentionally limited to pure core logic (order-state machine, position math, risk invariants). The suite trusts **real infrastructure, real-deployed environments, and real provider responses (recorded)**.

Target test mix: **Integration ~45% . E2E ~35% . Unit ~20%**

## 2. Levels

| # | Level | Tools | Runs on | Scope |
|---|---|---|---|---|
| T1 | Test planning | Test strategy doc, traceability matrix | -- | every requirement -> >=1 test |
| T2 | Test design | Gherkin `.feature` + Playwright specs | -- | buy/hold/sell/risk-blowup/chaos scenarios |
| T3 | **Integration** | pytest + **testcontainers** (real Postgres, ClickHouse, Redis) + **vcrpy** (recorded provider responses) + WireMock (graphql/http stubs) | CI, dev | adapter<->bus, repo<->DB, slice->slice over real infra, outbox delivery/redelivery, provider rate-limit & failover, anti-corruption boundaries |
| T4 | **E2E** | **Playwright** (browser) + **API E2E** (REST/WS against **deployed** stack): CF Workers web + VPS engine + DBs | per-PR (smoke) + staging (full) + release candidate | login->trade flow, LLM proxy, WS real-time updates, kill-switch, strategy promotion, provider outage behavior |
| T5 | Contract | pact-style validation of `web/`<->engine OpenAPI + slice contracts | CI | schema drift detection before any deploy |
| T6 | Backtest regression | walk-forward, seed-locked; metric gates Sharpe + MDD | CI/nightly | retraining/optimizer must not regress |
| T7 | Load/Perf | Locust + k6 | staging | peak ticks, 10k WS, API p95 |
| T8 | Chaos | fault injection API + dedicated scenarios | staging/release | kill Redis, drop exchange, LLM 500s, suspend VPS network, kill worker |
| T9 | Security | OWASP ZAP, Bandit/Semgrep, pip-audit, gitleaks | CI + release | auth bypass, injection, secret leakage |
| T10 | UAT/demo | graded walkthrough | pre-prod | stakeholder sign-off |
| T11 | Regression | per-PR smoke = integration subset + E2E smoke; nightly = **full integration + full E2E** | CI | no escapes |

## 3. Gates

- **PR:** lint + types + unit (core) + **integration suite (minimal, real containers)** + E2E smoke on preview.
- **Release candidate:** **full integration suite + full E2E** (Playwright + API E2E) against deployed staging stack; then load + chaos + security.
- **Nightly:** full regression (integration + E2E + backtest gates) on staging data.
- **Hard rule:** CI **never** sends orders to live markets -- paper / `live-simulated` only.

## 4. Infrastructure for tests

- `testcontainers` spins PG/ClickHouse/Redis per test session (parallelized).
- `vcrpy` cassette store in repo (`tests/cassettes/`) -- deterministic, offline-capable integration runs.
- E2E environments: nightly-deployed staging replicating prod topology (Workers + VPS + DBs).
- Seeded fixtures: deterministic market data generators; seed-locked for backtests.