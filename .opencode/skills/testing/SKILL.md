---
name: testing
description: Test strategy and validation gates. Integration-first. Gate selection by change type. Definition of done.
---

# Testing and Gates

Load this skill: before running tests, before declaring a change done, or when adding new tests.

Reference: `docs/STLC-PLAN.md` for test levels and infrastructure. `docs/CONVENTIONS.md` for DoD checklist.

---

## Test Strategy

Integration-first and E2E-first. Not a unit pyramid. The domain logic is small and pure; risk lives at boundaries.

Target mix: Integration ~45%, E2E ~35%, Unit ~20%.

## Test Layout

```
tests/
  unit/           pure domain/application (state machines, math, invariants)
  integration/    real PG/ClickHouse/Redis via testcontainers + vcrpy cassettes
  e2e/            full stack against deployed or composed env
  cassettes/      vcrpy recordings, secrets scrubbed
```

## What Tests Go Where

| Boundary | Test Type |
|---|---|
| Domain behavior | Unit tests |
| Application workflow | Application tests |
| Port/adapter contract | Integration tests |
| Presentation routes | API tests |
| Complete critical workflow | E2E tests |

Domain tests must NOT require: PostgreSQL, Redis, ClickHouse, FastAPI, external APIs.

## Validation Gates

### Backend (always run)

```bash
uv run ruff check app tests
uv run mypy app
uv run lint-imports
uv run pytest -q
```

### Integration (when touching adapters, stores, or bus)

```bash
uv run pytest -m integration
```

### Web (when touching web/)

```bash
pnpm --dir web lint
pnpm --dir web exec tsc --noEmit
pnpm --dir web exec playwright test
```

### Security (before merge)

```bash
pip-audit && npm audit && gitleaks detect
```

## Gate Selection by Change Type

| Change | Required Gates |
|---|---|
| Domain entity only | ruff, mypy, unit |
| New use-case | ruff, mypy, lint-imports, unit |
| New adapter | ruff, mypy, lint-imports, integration |
| New route | ruff, mypy, lint-imports, API test |
| New slice | all backend gates |
| Cross-module | all backend gates |

## Definition of Done

- [ ] Lint, types, import contracts green
- [ ] Unit + integration green, coverage >= 85%
- [ ] New service in `app/di.py`, router in `app/routers.py`
- [ ] Vendor errors mapped, no SDK exception escapes adapter
- [ ] No secret logged, committed, or in cassette
- [ ] Conventional Commit, one logical change
