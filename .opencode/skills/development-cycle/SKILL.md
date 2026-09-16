---
name: development-cycle
description: Full development cycle from task initiation to deployment. Load when starting any new task or when asked about the development workflow.
---

# Development Cycle

Complete workflow from receiving a task to deploying it.

Reference: `docs/SDLC-PLAN.md` for sprint phases. `docs/DEVOPS-PLAN.md` for CI/CD pipeline.

---

## Phase 1: Understand the Task

Before writing any code, answer these questions:

1. What is the user asking for?
2. Which module owns this? (`auth`, `marketdata`, `signals`, `strategies`, `backtest`, `risk`)
3. Does a new module need to exist, or does an existing one handle it?
4. Is this a domain change, application change, adapter addition, or route addition?
5. What existing code does something similar?

Read the relevant skill:
- Modifying a module -> `backend-slice`
- Adding a provider -> `integrations`
- Creating a new module -> `scaffold`
- Unclear about architecture -> `architecture`

## Phase 2: Implement Outside-In

Follow this order. Do not skip steps.

```
domain/entities.py       1. Business models, value objects, enums
domain/ports.py          2. Capability interfaces (Protocol classes)
domain/events.py         3. Cross-slice events (only if needed)
application/services.py  4. Use-cases returning Result[T, DomainError]
infrastructure/          5. Adapter implementing the port
presentation/routes.py   6. HTTP endpoint
presentation/schemas.py  7. Request/response shapes
app/di.py                8. Register service
app/routers.py           9. Include router
```

After each file, verify the module compiles:

```bash
uv run ruff check app/modules/<name>/
uv run mypy app/modules/<name>/
```

## Phase 3: Test

Write tests that match the boundary:

| What Changed | Test Type | Where |
|---|---|---|
| Domain logic | Unit test | `tests/unit/` |
| Application workflow | Application test | `tests/unit/` |
| Adapter | Integration test | `tests/integration/` |
| Route | API test | `tests/integration/` |
| Full critical flow | E2E test | `tests/e2e/` |

Domain tests must not require databases, Redis, or external APIs.

## Phase 4: Validate Gates

Run gates in order. Fix any failure before proceeding.

```bash
# Step 1: Formatting and linting
uv run ruff check app tests

# Step 2: Type checking
uv run mypy app

# Step 3: Architecture contracts
uv run lint-imports

# Step 4: Unit tests
uv run pytest -q

# Step 5: Integration tests (if adapter/store/bus changed)
uv run pytest -m integration

# Step 6: Security scan (before merge)
pip-audit && gitleaks detect
```

If any gate fails, fix the issue. Do not skip or loosen thresholds.

## Phase 5: Architecture Review

Before declaring done, verify:

```bash
# No SDK leaks into domain/application
grep -rn "import ccxt\|import redis\|import sqlalchemy\|import fastapi" \
  app/modules/<name>/domain/ app/modules/<name>/application/
# Should return nothing

# No cross-module internal access
grep -rn "from app.modules\.\(.*\)\.\(infrastructure\|application\|presentation\)" \
  app/modules/ --include="*.py" | grep -v "contracts"
# Should return nothing (or only contracts/ imports)

# Import contracts pass
uv run lint-imports
```

## Phase 6: Commit

Use Conventional Commits. One logical change per commit.

```
feat(<module>): <description>
fix(<module>): <description>
test(<module>): <description>
refactor(<module>): <description>
docs: <description>
```

Examples:
```
feat(marketdata): add candle query endpoint
fix(auth): use result.is_err instead of isinstance
test(risk): add integration test for kill switch
refactor(signals): extract feature computation to domain service
```

## Phase 7: Deploy

CI/CD pipeline order:

```
lint -> typecheck -> unit -> integration -> coverage >= 85% -> SAST -> build -> E2E
```

Deployment targets:
- Python engine: Docker on VPS (watchtower, blue-green)
- web/: Cloudflare Workers via @opennextjs/cloudflare (Vercel fallback)
- Infrastructure: Terraform (DNS, Workers, R2)

Rollback: keep previous image tagged. Flip back.

---

## Quick Reference: What to Do When

| Situation | Action |
|---|---|
| "Add an endpoint for X" | Load `backend-slice`. Implement outside-in. |
| "Connect to Binance" | Load `integrations`. Create adapter. |
| "Create a sentiment module" | Load `scaffold`. Run new_slice.py. |
| "Run the tests" | Load `testing`. Select gates by change type. |
| "Clean up this code" | Load `refactor`. Preserve behavior. |
| "Is this architecture correct" | Load `architecture`. Check violations. |
| "I'm done, what now" | Load `testing`. Run full gate suite. |
