# Engineering Conventions

Status: DRAFT · Enforced by tooling + review

---

## 1. Commits & Branches
- Conventional Commits: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `ci:`, `chore:`.
- Branch: `feat/<slug>`, `fix/<slug>`, `test/<slug>`; trunk-based; short-lived.
- One logical change per commit; imperative mood.

## 2. Python (`app/`)
- Python 3.12; `pyproject.toml` single source of truth (ruff, mypy).
- **Type-checking:** mypy strict; `Result[T, E]` for use-case returns (no naked `try/except` plumbing).
- **Style:** ruff (defaults + isort-style import sorting); line length 100.
- **Naming:** slices `<snake>_<slice>`; routers `*_router.py`; use-cases `*_handler.py`/`*_service.py`; contracts `*_event.py`/`*_command.py`.
- **Domain:** Pydantic v2 models for schemas/contracts; dataclasses/`dataclasses` for domain entities where appropriate; enums over strings.
- **No comments unless clarifying intent** (code should be self-evident); docstrings for public APIs.
- Structure inside each slice: `api/ application/ domain/ infrastructure/ contracts/` — keep it; `import-linter` enforces.

## 3. TypeScript / Next.js (`web/`)
- Next.js 16 App Router; TypeScript strict; React 19.
- Server components by default; client code under `"use client"` only where interactivity requires.
- No secrets in client components (`!SECRET` guard); `NEXT_PUBLIC_` only for public config.
- Route Handlers under `app/api/<name>/route.ts`; edge-safe `middleware.ts`.
- Styling: Tailwind 4; charts via Tremor/Recharts.

## 4. Logging & Errors (all runs)
- `structlog` JSON; every scope has `correlation_id`.
- Use error taxonomy classes (`core.exceptions`), never bare `except:`.
- Log context: `event, slice, correlation_id, duration_ms, outcome`.
- **Never log** api keys, tokens, passwords, order secrets.

## 5. Testing (integration-first, E2E-first — see STLC-PLAN.md)
- Integration tests talk to real PG/ClickHouse/Redis (testcontainers) + recorded provider cassettes (vcrpy).
- E2E: Playwright (web) + API E2E against deployed stack; add/update specs in `web/e2e/`.
- Unit: only pure core (state machines, math, invariants) in `tests/unit/`.
- Coverage gate ≥85%; seeded, seed-locked backtests.
- A PR is not done until its integration/E2E smoke passes.

## 6. Definition of Done
- Green: lint, types, unit, **integration**, **E2E smoke**, contract, SAST/SCA, secrets scan.
- Mypy/tsc-clean; coverage gate; docs updated if behaviour changed (OpenAPI regenerated); conventional commit; ADR conformant.