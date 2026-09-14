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

## Improve-until-plateau loop (optimization sprints / self-improvement)

When the task is "make the app better" (optimization sprint or `selfimprovement` slice work), do **not** tweak once and stop. Run an **event loop of rounds** until the app stops getting better, then stop and report.

1. **Baseline first** — capture the metric before touching code: `uv run ruff check app tests`, `uv run mypy app`, `uv run pytest -q`, plus the backtest score you are optimizing (e.g. win rate / drawdown / Sharpe).
2. **One scoped change per round** — never batch unrelated edits into a single round.
3. **Verify every round** — re-run all gates. A regression in lint/mypy/tests/coverage fails the round (revert or fix before the next round).
4. **Measure** — re-capture the metric and compare to the best-so-far.
5. **Promote or revert** — improved → keep (Conventional Commit); equal → revert and try another angle; worse → revert.
6. **Stop on plateau** — after `max_stale_rounds` (default **3**) consecutive non-improving rounds, STOP. Do not chase infinite tweaks. Report: baseline → final, what was tried, what won, why each loser lost.
7. **Events/LLM agents:** signal every round/promotion/plateau via the event bus and `get_logger("app.workers.runner")` (see `app/workers/runner.py`) so other agents/LLMs can observe the loop and continue from `best` rather than restarting.

### How to run it as an event loop

- **Engine event loop** (the runtime self-improvement cycle): `uv run python -m app.workers.runner`. It builds the container, runs the `ImproveUntilPlateau` loop (each round = a `RoundStep` through `Container`), promotes on metric improvement, plateaus after `max_stale_rounds`, and shuts down gracefully on SIGINT/SIGTERM. Tuned via `SELF_IMPROVE__*` env vars (see `.env.example`).
- **Agent dev loop** (you, the coding agent): the verify→measure→promote cycle above IS the loop; run it inside the same shell session, one round per asyncio iteration, with `max_rounds`/plateau guardrails. Do not make a coding agent run indefinitely without a stop condition.

**Guardrails:** never loosen the fail-closed risk gate; never drop coverage below 85%; never skip a gate; self-improvement can never override the risk manager; every change stays rollbackable (single commit per round).