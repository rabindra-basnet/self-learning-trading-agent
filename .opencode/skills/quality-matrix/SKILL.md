---
name: quality-matrix
description: Code quality matrix for evaluating this application. Load when reviewing code, running audits, or checking if a change meets standards.
---

# Code Quality Matrix

Use this to evaluate any code in this repository.

---

## 1. Architecture Compliance (pass/fail)

| Rule | Pass | Fail |
|---|---|---|
| Domain imports nothing from infrastructure | `domain/` only imports `app.core` and stdlib | `domain/` imports fastapi, redis, ccxt, sqlalchemy, pandas |
| Application depends only on ports | `application/` imports `domain/ports.py` | `application/` imports concrete adapter classes |
| Presentation is thin | `presentation/` resolves service, translates Result to HTTP | `presentation/` contains business logic, DB queries |
| Infrastructure implements ports | `infrastructure/` imports `domain/ports.py` | `infrastructure/` imports other slices |
| No cross-module internal access | Module A only imports Module B's `contracts/` | Module A imports Module B's `infrastructure/` or `application/` |
| Composition root wires everything | `app/di.py` registers all services | Services created inside routes or use-cases |

## 2. Code Quality (scored)

| Metric | 0 | 1 | 2 |
|---|---|---|---|
| Type safety | Missing type hints | Basic hints, no strict mypy | mypy strict, no `Any`, no `type: ignore` |
| Error handling | Bare `except`, swallowed errors | `try/except` with logging | `Result[T, DomainError]`, mapped at boundary |
| Naming | Generic names (`data`, `result`, `handler`) | Descriptive but inconsistent | Domain vocabulary (`CandleStore`, `RiskProfile`, `SignalEmitted`) |
| Single responsibility | God function, 200+ lines | Mixed concerns | One function does one thing |
| Dependency direction | Inner layers import outer | Mostly correct | Strict inward-pointing dependencies |
| Logging | No logging, bare print, or swallowed errors | Basic `print()` or `logging.info` without structure | Structured logging with `structlog`, context fields, correlation_id |
| Test coverage | No tests | Happy-path only | Edge cases, error paths, boundary contracts |

### Logging rules

- Use `structlog` for all application logs
- Every log entry must include `correlation_id` (request context)
- No secrets, API keys, or tokens in log output
- Log domain events at application boundary
- Log infrastructure errors at adapter boundary
- Never log full order payloads (use order_id only)
- Log levels: DEBUG (dev), INFO (decisions), WARNING (retries), ERROR (failures), CRITICAL (kill-switch)

```python
import structlog

logger = structlog.get_logger(__name__)

# Correct
logger.info("order_submitted", order_id=order.id, symbol=symbol, side="buy")
logger.error("provider_failure", provider="binance", error=str(e), correlation_id=ctx.correlation_id)

# Wrong
print(f"Order submitted {order}")           # bare print
logger.info(f"Key is {api_key}")            # secret leak
logger.error(e)                              # no context
```

## 3. Integration Quality (pass/fail)

| Rule | Pass | Fail |
|---|---|---|
| Vendor errors mapped | Every SDK exception -> one `DomainError` subclass | SDK exception reaches `application/` or `presentation/` |
| Vendor types normalized | Domain entities only in inner layers | `ccxt.Ticker`, `redis.Response` in `domain/` |
| Port matches capability | Port named by business need (`MarketDataProvider`) | Port named by vendor (`BinanceAPI`) |
| Adapter is replaceable | Swapping provider = new adapter + config only | Swapping provider = touching domain/application code |

## 4. Operational Quality (pass/fail)

| Rule | Pass | Fail |
|---|---|---|
| No secrets in code | Keys via `SecretStr`, read at composition root | Hardcoded keys, `.env` committed |
| No secrets in logs | Structured logs, redacted fields | API keys, tokens in log output |
| No secrets in cassettes | `filter_headers` and `filter_query_parameters` set | Live keys in vcrpy recordings |
| Graceful degradation | Provider failure -> mapped error, retry, or fallback | Unhandled exception crashes the service |
| Idempotent operations | Events deduplicated by ID, writes use upsert | Duplicate processing on retry |

## 5. Test Quality (scored)

| Metric | 0 | 1 | 2 |
|---|---|---|---|
| Boundary coverage | Only happy path tested | Happy + error paths | Contract suites per port, adapter swap confidence |
| Test independence | Tests depend on execution order, shared state | Mostly isolated | Each test sets up its own state, cleans up |
| Real infrastructure | All mocked, no real containers | Some integration tests | testcontainers for PG/ClickHouse/Redis, vcrpy for providers |
| Determinism | Flaky tests, random failures | Seed-locked where needed | Seed-locked backtests, cassettes for providers |
| Coverage | < 60% | 60-85% | >= 85% |

## 6. Quick Audit Commands

```bash
# Architecture violations
grep -rn "import ccxt\|import redis\|import sqlalchemy\|import fastapi" \
  app/modules/*/domain/ app/modules/*/application/

# Cross-module leaks
grep -rn "from app.modules\.\(.*\)\.\(infrastructure\|application\|presentation\)" \
  app/modules/ --include="*.py" | grep -v "contracts"

# Import contracts
uv run lint-imports

# Type safety
uv run mypy app

# Lint
uv run ruff check app tests

# Logging check: no bare print in application code
grep -rn "print(" app/modules/ --include="*.py"

# Logging check: no secrets in logs
grep -rn "logger\.\(info\|error\|warning\|debug\).*\(key\|secret\|token\|password\)" app/ --include="*.py"

# Test coverage
uv run pytest --cov=app --cov-report=term-missing
```

## 7. Pre-Commit Quality Gate

Run `.agents/scripts/pre_commit_quality.py` before every commit. It checks:

1. Architecture violations (SDK imports in domain/application)
2. Cross-module leaks
3. Import contracts (lint-imports)
4. Type safety (mypy)
5. Logging violations (bare print, secrets in logs)
6. Secrets in code
7. Test coverage threshold (>= 85%)

```bash
python .agents/scripts/pre_commit_quality.py
```

## 8. Scoring

| Area | Weight | How to score |
|---|---|---|
| Architecture compliance | 40% | Pass/fail per rule. Any fail = 0 for area. |
| Code quality | 20% | Sum of 0/1/2 scores, normalize to 100. |
| Integration quality | 15% | Pass/fail per rule. Any fail = 0 for area. |
| Operational quality | 10% | Pass/fail per rule. Any fail = 0 for area. |
| Test quality | 15% | Sum of 0/1/2 scores, normalize to 100. |

Overall score: weighted sum. Target: >= 80.

A score below 60 means the code needs refactoring before adding features.
