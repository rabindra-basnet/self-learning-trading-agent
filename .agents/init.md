# Feature Guide -- What's Done, What's Broken, What's Next

This file is auto-loaded at startup. Use it to plan work.

---

## Status Overview

| Module | Status | Priority |
|--------|--------|----------|
| marketdata | COMPLETE (1 bug) | Fix bug |
| signals | COMPLETE (1 gap) | Add Result type |
| strategies | BROKEN (3 runtime bugs) | Fix first |
| backtest | BROKEN (3 runtime bugs) | Fix second |
| risk | COMPLETE | Ready |
| auth | COMPLETE (1 bug) | Fix bug |
| core | COMPLETE (1 bug) | Fix bug |
| web/ | NOT SCAFFOLDED | Scaffold when backend stable |
| tests/ | EMPTY | Write after bugs fixed |
| infra/ | PARTIAL | Add terraform, CI |

---

## Runtime-Breaking Bugs (fix before anything else)

| # | File | Issue | Skill |
|---|------|-------|-------|
| 1 | `app/di.py:61` | `configure_logging()` called with no args, requires `env: str` | `refactoring` |
| 2 | `app/di.py:145-146` | `StrategyManager` constructor receives 2 args, expects 1 | `refactoring` |
| 3 | `app/di.py:167` | `builtin_strategies()` function does not exist (only `BUILTIN_STRATEGIES` dict) | `refactoring` |
| 4 | `app/modules/strategies/application/manager.py:15` | `StrategyManager` missing `register()`, `get_strategy()`, `list_meta()` methods | `backend-slice` |
| 5 | `app/modules/backtest/application/engine.py:37` | `self._manager.get_strategy()` does not exist | `backend-slice` |
| 6 | `app/modules/backtest/application/engine.py:51` | `self._bus.publish()` not awaited (async event silently lost) | `backend-slice` |
| 7 | `app/modules/strategies/presentation/routes.py:16` | `_get_manager` returns `Container` not `StrategyManager` | `backend-slice` |
| 8 | `app/modules/auth/presentation/routes.py:62` | Resolves `UserRepository` protocol but container binds concrete type | `backend-slice` |

## Architectural Bugs (fix after runtime bugs)

| # | File | Issue | Skill |
|---|------|-------|-------|
| 9 | `app/modules/strategies/application/manager.py:8` | `application` imports from `presentation.schemas` (violates hexagonal) | `architecture` |
| 10 | Multiple files (7 occurrences) | `isinstance(result, Err)` instead of `result.is_err` | `architecture` |

## Missing Components

| Component | Status | Skill |
|-----------|--------|-------|
| `tests/` | Empty | `testing` |
| `web/` | Not scaffolded | `frontend` |
| `infra/terraform/` | Missing | `security` |
| `infra/.github/workflows/` | Missing | `security` |
| `app/modules/llm/` | Not created | `scaffold` |
| `app/modules/backtest/domain/__init__.py` | Missing | `backend-slice` |
| `app/modules/backtest/application/__init__.py` | Missing | `backend-slice` |
| `app/modules/strategies/domain/__init__.py` | Missing | `backend-slice` |

---

## Work Order (recommended sequence)

### Phase 1: Fix Runtime Bugs (unblock everything)

```
Step 1: Fix di.py logging call
  skill(name="refactoring")
  File: app/di.py line 61
  Change: configure_logging() -> configure_logging(env=settings.env)

Step 2: Fix StrategyManager wiring
  skill(name="backend-slice")
  Files: app/modules/strategies/application/manager.py, app/di.py
  Fix: Add missing methods to StrategyManager, fix constructor args

Step 3: Fix builtin_strategies import
  skill(name="refactoring")
  File: app/di.py line 167
  Change: builtin_strategies() -> BUILTIN_STRATEGIES

Step 4: Fix backtest engine async
  skill(name="backend-slice")
  File: app/modules/backtest/application/engine.py line 51
  Change: self._bus.publish(...) -> await self._bus.publish(...)

Step 5: Fix strategies routes type mismatch
  skill(name="backend-slice")
  File: app/modules/strategies/presentation/routes.py line 16
  Fix: Resolve StrategyManager from container, not Container

Step 6: Fix auth routes type mismatch
  skill(name="backend-slice")
  File: app/modules/auth/presentation/routes.py line 62
  Fix: Bind protocol in container or resolve concrete type

Step 7: Add missing __init__.py files
  skill(name="backend-slice")
  Files: app/modules/backtest/domain/__init__.py, app/modules/backtest/application/__init__.py, app/modules/strategies/domain/__init__.py
```

### Phase 2: Fix Architectural Bugs

```
Step 8: Fix isinstance(result, Err) pattern (7 occurrences)
  skill(name="architecture")
  Files: marketdata/routes.py, backtest/engine.py, backtest/routes.py, auth/routes.py
  Change: isinstance(result, Err) -> result.is_err

Step 9: Fix strategies application importing from presentation
  skill(name="architecture")
  File: app/modules/strategies/application/manager.py line 8
  Change: Move StrategyMeta import to domain.entities
```

### Phase 3: Add Missing Features

```
Step 10: Add Result type to signals FeatureService
  skill(name="backend-slice")
  File: app/modules/signals/application/services.py
  Change: Return Result[List[FeatureVector], DomainError] instead of raw list

Step 11: Write tests
  skill(name="testing")
  Priority: marketdata, risk, auth, signals, strategies, backtest

Step 12: Scaffold web/ frontend
  skill(name="frontend")
  Reference: .opencode/skills/frontend/SKILL.md

Step 13: Add LLM module
  skill(name="scaffold")
  Reference: .opencode/skills/scaffold/SKILL.md
```

### Phase 4: Infrastructure & Security

```
Step 14: Add terraform
  skill(name="security")

Step 15: Add GitHub Actions CI
  skill(name="security")

Step 16: Security audit
  skill(name="quality-matrix")
  skill(name="security")
```

---

## Module Completeness Matrix

| Module | domain | application | infrastructure | presentation | contracts | Status |
|--------|--------|-------------|----------------|--------------|-----------|--------|
| marketdata | YES | YES | YES (binance) | YES | YES | COMPLETE (1 bug) |
| signals | YES | YES | YES (pandas) | YES | YES | COMPLETE (1 gap) |
| strategies | YES | PARTIAL | YES (library) | YES | YES | BROKEN |
| backtest | YES | YES | -- | YES | YES | BROKEN |
| risk | YES | YES | YES (in-mem) | YES | YES | COMPLETE |
| auth | YES | YES | YES (in-mem+pg) | YES | YES | COMPLETE (1 bug) |

---

## Quick Reference

```bash
# Check module status
ls app/modules/<name>/

# Verify architecture
uv run lint-imports

# Type check
uv run mypy app

# Lint
uv run ruff check app tests

# Test
uv run pytest -q

# Pre-commit quality gate
python .agents/scripts/pre_commit_quality.py
```
