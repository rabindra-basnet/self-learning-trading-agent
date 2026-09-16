# AGENTS.md — Repository Guide for AI Coding Agents

Follow this document for every task. Read the referenced docs before editing.

## CRITICAL: Load skills before every task

**You MUST use the `skill` tool to load the relevant skill BEFORE starting any task.** Do not wait for the user to ask.

```
skill(name="architecture")      -- ALWAYS, before any code change
skill(name="development-cycle") -- at start of any task
skill(name="backend-slice")     -- when modifying a module
skill(name="frontend")          -- when touching web/
skill(name="security")          -- when handling secrets/auth
skill(name="refactoring")       -- when restructuring code
skill(name="quality-matrix")    -- when reviewing/auditing
skill(name="integrations")      -- when adding a provider
skill(name="testing")           -- when running tests
skill(name="scaffold")          -- when creating a new module
```

## Repo shape

```
app/   Python trading engine (VSA modular monolith, FastAPI)
web/   Unified Next.js 16 app (dashboard + API edge + LLM proxy) — NOT scaffolded yet
docs/  PRD · SDLC · STLC · DEVOPS · SYSTEM-DESIGN · SECURITY · CONVENTIONS
infra/ Terraform · docker-compose · GitHub Actions · runbooks
```

## Hard rules

1. **No business code until documented.** This repo is in S0 (planning/scaffold). Phases are gated — see `docs/SDLC-PLAN.md`.
2. **Vertical slices, strict deps:** slices in `app/modules/<slice>/` may import `app/core/` and other slices' `contracts/` only. Slice→slice internal imports are CI-failing (import-linter). **Hexagonal isolation: `domain/` and `application/` must NEVER import providers/frameworks/SDKs — all third-party code lives in `app/infrastructure/` or slice `infrastructure/` and is reached through ports; see `docs/INTEGRATION-ARCHITECTURE.md`.**
3. **Integration-first + E2E-first testing** (not unit-pyramid): `docs/STLC-PLAN.md`.
4. **Never log or commit secrets.** No plaintext keys, tokens, passwords, `.env`.
5. Follow `docs/CONVENTIONS.md` (commits, naming, typing, logging, errors, DoD).

## Conventions & style

- Python 3.12, mypy strict, ruff, `Result[T,E]` use-cases, Pydantic v2, no bare `except`.
- TypeScript strict, React 19, Next.js 16 App Router, edge-safe middleware, `NEXT_PUBLIC_` only.
- Conventional Commits; trunk-based short branches.

## Workflow commands (landing each layer)

**Before declaring anything done, run ALL gates in order:**

```bash
# Backend gates
uv run ruff check app tests
uv run mypy app
uv run lint-imports
uv run pytest -q                    # unit (default marker)
uv run pytest -m integration        # real containers + cassettes
uv run pytest -m e2e

# Web gates (when web/ is scaffolded)
pnpm --dir web lint
pnpm --dir web exec tsc --noEmit
pnpm --dir web exec playwright test

# Security / deps
pip-audit && npm audit && gitleaks detect
```

Exact flags may vary per sprint; keep this file in sync with `docs/CONVENTIONS.md`.

## Testing stack

pytest + testcontainers + vcrpy + Playwright + WireMock | mypy/ruff gates | coverage ≥85% | seeded/seed-locked backtests.

## Key gotchas (things agents get wrong here)

**Import-linter contracts (CI-breaking):**
- When adding a new slice, edit `pyproject.toml` in **three** places: (1) new slice's own contract, (2) add the new slice to **every other slice's** `forbidden_modules`, (3) add the new slice's `domain`/`application` modules to the provider-free contract's `source_modules`. Step 2 is the one that gets skipped — skipping it means old slices can import the new one with no CI complaint.
- Verify with `uv run lint-imports`.

**Composition root wiring (runtime-breaking):**
- New service → register in `app/di.py` **and** include router in `app/routers.py`. Doing one without the other causes silent failures: unregistered service = runtime error on first request; unregistered router = route 404.
- New settings → `app/core/config/settings.py` **and** `.env.example`. Secrets use `SecretStr`, read via `.get_secret_value()` at composition root only.

**Result / Ok / Err (silent bug):**
- `Ok` and `Err` are factory *functions*, not classes — `isinstance(result, Err)` is always `False` and silently swallows the error path. Use `result.is_err` and call `result.error_value()` / `result.ok_value()` as methods.
- There is an existing instance of this bug in `app/modules/marketdata/presentation/routes.py`; fix it rather than copying it.

**Vendor errors must never cross the adapter boundary:**
- Every vendor exception maps to exactly one `DomainError` subclass in `infrastructure/providers/<vendor>/errors.py`. If `ccxt.NetworkError` reaches `application/`, the use-case is coupled to ccxt and the port was pointless.

**web/ is not scaffolded yet:**
- If a task needs the web side, scaffold per `trading-agent-fullstack/references/web-app.md`. The same Next.js 16 package deploys to Cloudflare Workers (primary) and Vercel (fallback).

## Improve-until-plateau loop

When the task is "make the app better", run an **event loop of rounds** until the metric stops improving, then stop and report. Full workflow: baseline → one scoped change per round → verify all gates → measure → promote or revert → stop after 3 consecutive non-improving rounds. See the `trading-agent-fullstack` skill for the complete event loop spec and guardrails.

**Guardrails:** never loosen the fail-closed risk gate; never drop coverage below 85%; never skip a gate; self-improvement can never override the risk manager; every change stays rollbackable (single commit per round).

## References

- `.agents/init.md` — feature guide, work order, module status (auto-loaded)
- `.opencode/skills/` — all skills (loaded on-demand by agent)
- `.agents/commands.md` — quick command reference
- `.agents/scripts/new_slice.py` — scaffold a new module

## LLM / Agentic integration

- LLM provider config exists in `app/core/config/settings.py` (`LlmSettings`) but the hexagonal wiring (port → adapter → use-case) is not built yet.
- Default gateway: `https://opencode.ai/zen/v1` with `nemotron-3-ultra-free` model.
- **Planned agentic framework: LangChain** — will live in `app/modules/llm/` as a new slice following the same hexagonal pattern (domain port `LLMReasoner`, infrastructure adapter `langchain/`).

## Runtime Bugs (8 blocking issues)

| # | File | Issue | Skill |
|---|------|-------|-------|
| 1 | `app/di.py:61` | `configure_logging()` missing `env` arg | `refactoring` |
| 2 | `app/di.py:145-146` | `StrategyManager` constructor args mismatch | `backend-slice` |
| 3 | `app/di.py:167` | `builtin_strategies()` does not exist | `refactoring` |
| 4 | `strategies/application/manager.py:15` | Missing `register()`, `get_strategy()`, `list_meta()` | `backend-slice` |
| 5 | `backtest/application/engine.py:37` | `get_strategy()` does not exist | `backend-slice` |
| 6 | `backtest/application/engine.py:51` | `self._bus.publish()` not awaited | `backend-slice` |
| 7 | `strategies/presentation/routes.py:16` | Returns `Container` not `StrategyManager` | `backend-slice` |
| 8 | `auth/presentation/routes.py:62` | Protocol vs concrete type mismatch | `backend-slice` |

## Architectural Bugs (7 occurrences)

| # | Pattern | Files | Skill |
|---|---------|-------|-------|
| 9 | `isinstance(result, Err)` | marketdata/routes, backtest/engine, backtest/routes, auth/routes | `architecture` |
| 10 | application imports presentation | strategies/manager.py:8 | `architecture` |
