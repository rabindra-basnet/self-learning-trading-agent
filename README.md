# Self-Improving AI Trading Agent

Multi-asset (Crypto → Stocks → Forex) trading agent that improves itself through strategy optimization, ML retraining, LLM-powered analysis, and reinforcement learning — with strict risk controls and a minimal-cost, serverless-friendly footprint.

**Status:** S0 — planning/scaffold. No business code until the SDLC gate clears (see `docs/SDLC-PLAN.md`).

## Architecture

```
BROWSER
   │
   ▼
Cloudflare (DNS · CDN · WAF · DDoS · rate-limit)
   │
   ├──▶ web/  Next.js 16 (Workers Assets + Route Handlers + Edge middleware)  [PRIMARY]
   │         …same package also deployable to Vercel unchanged                [FALLBACK]
   │
   └──▶ [Minimal VPS]  Docker  ──▶ Python Trading Engine (FastAPI, WS, workers)
         ├─ PostgreSQL      ├─ ClickHouse      └─ Redis
```

- **`app/`** — Python trading engine: VSA modular monolith (FastAPI). Vertical slices in `app/modules/<slice>/` over a shared kernel in `app/core/`; ports & adapters keep domain/application layers provider-free.
- **`web/`** — Single Next.js 16 app = dashboard UI + API edge (Route Handlers) + LLM proxy + Edge middleware. Deploys to Cloudflare Workers or Vercel as one unit.
- **`docs/`** — PRD · SDLC · STLC · DEVOPS · SYSTEM-DESIGN · SECURITY · CONVENTIONS · INTEGRATION-ARCHITECTURE.
- **`infra/`** — Terraform, docker-compose, GitHub Actions, runbooks.

## Getting started

Local dev runs the web app and the engine together:

```bash
# the engine stack (PostgreSQL / Redis / ClickHouse / panopticum)
docker compose -f infra/docker-compose.yml up -d

# backend engine — uv (Python 3.12)
uv sync
uv run uvicorn app.main:app --reload

# web app (pnpm workspace)
pnpm --dir web install && pnpm --dir web dev
```

## Documentation

| Doc | Purpose |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Product requirements & acceptance criteria |
| [`docs/SDLC-PLAN.md`](docs/SDLC-PLAN.md) | Master plan, phasing & gates |
| [`docs/STLC-PLAN.md`](docs/STLC-PLAN.md) | Integration-first + E2E-first test strategy |
| [`docs/SYSTEM-DESIGN.md`](docs/SYSTEM-DESIGN.md) | System design (VSA, slices, DBs, web app) |
| [`docs/INTEGRATION-ARCHITECTURE.md`](docs/INTEGRATION-ARCHITECTURE.md) | Ports & adapters / hexagonal rules |
| [`docs/DEVOPS-PLAN.md`](docs/DEVOPS-PLAN.md) | CI/CD, deploy topology, SLOs, runbooks |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Threat model, secrets, RBAC |
| [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) | Commits, naming, typing, DoD |

## Development workflow

```bash
# backend
uv run ruff check app tests
uv run mypy app
uv run pytest -q                          # unit
uv run pytest -m integration              # real containers via testcontainers + vcrpy
uv run pytest -m e2e

# web
pnpm --dir web lint
pnpm --dir web exec playwright test
```

See `AGENTS.md` for the full command reference and contribution rules.

## License

© 2026 · Private repository — not for public distribution.