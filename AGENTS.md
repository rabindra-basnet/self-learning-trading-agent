# AGENTS.md — Repository Guide for AI Coding Agents

Follow this document for every task. Read the referenced docs before editing.

## Repo shape

```
app/   Python trading engine (VSA modular monolith, FastAPI)
web/   Unified Next.js 16 app (dashboard + API edge + LLM proxy)
docs/  PRD · SDLC · STLC · DEVOPS · SYSTEM-DESIGN · SECURITY · CONVENTIONS
infra/ Terraform · docker-compose · GitHub Actions · runbooks
```

## Hard rules

1. **No business code until documented.** This repo is in S0 (planning/scaffold). Phases are gated — see `docs/SDLC-PLAN.md`.
2. **Vertical slices, strict deps:** slices in `app/modules/<slice>/` may import `app/core/` and other slices' `contracts/` only. Slice→slice internal imports are CI-failing (import-linter). **Hexagonal isolation: `domain/` and `application/` must NEVER import providers/frameworks/SDKs — all third-party code lives in `app/infrastructure/` or slice `infrastructure/` and is reached through ports; see `docs/INTEGRATION-ARCHITECTURE.md`.** Check `AGENTS.md` updates if you change the map (SYSTEM-DESIGN §4).
3. **Integration-first + E2E-first testing** (not unit-pyramid): `docs/STLC-PLAN.md`. Integration tests use real containers (testcontainers) and recorded provider cassettes (vcrpy). E2E uses Playwright + API E2E against deployed envs.
4. **Never log or commit secrets.** No plaintext keys, tokens, passwords, `.env`.
5. Follow `docs/CONVENTIONS.md` (commits, naming, typing, logging, errors, DoD).

## Conventions & style

- Python 3.12, mypy strict, ruff, `Result[T,E]` use-cases, Pydantic v2, no bare `except`.
- TypeScript strict, React 19, Next.js 16 App Router, edge-safe middleware, `NEXT_PUBLIC_` only.
- Conventional Commits; trunk-based short branches.

## Workflow commands (landing each layer)

- Backend app: `uv run ruff check app tests`
- `uv run mypy app`
- `uv run pytest -q` (unit) · `uv run pytest -m integration` · `uv run pytest -m e2e`
- Web app: `pnpm --dir web lint` / `tsc --noEmit --project web/tsconfig.json`
- Web E2E: `pnpm --dir web exec playwright test`
- Deps/security: `pip-audit`, `npm audit`, `gitleaks detect`
- Deploys: `docker compose -f infra/docker-compose.yml up -d` (VPS) · `pnpm --dir web deploy` (CF Workers) · Vercel fallback.

Exact flags may vary per sprint; keep this file in sync with `docs/CONVENTIONS.md`. If a required command is unclear, ask the user before guessing.

## Testing stack (non-negotiable)

pytest + testcontainers + vcrpy + Playwright + WireMock | mypy/ruff gates | coverage ≥85% | seeded/seed-locked backtests.