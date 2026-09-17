# Commands

Agent-agnostic command reference. Any coding agent can follow these.

---

## new-module: Create a new business module

```bash
# Step 1: Scaffold
uv run python .agents/scripts/new_slice.py <name> --repo .
# or by description
uv run python .agents/scripts/new_slice.py --about "description" --repo .
```

```bash
# Step 2: Verify structure was created
ls app/modules/<name>/
# Should show: presentation/ application/ domain/ infrastructure/ contracts/
```

```bash
# Step 3: Run gates
uv run lint-imports && uv run ruff check app && uv run mypy app && uv run pytest -q
```

Important: After scaffolding, manually update pyproject.toml (3 places) and wire di.py + routers.py. The script prints exactly what to paste.

---

## feature: Add or modify a feature in a module

Work outside-in. Order matters:

```
1. domain/entities.py     - business models
2. domain/ports.py        - capability interfaces
3. domain/events.py       - cross-slice events (if needed)
4. application/services.py - use-cases returning Result[T, DomainError]
5. infrastructure/        - adapter implementing the port
6. presentation/routes.py - HTTP endpoint
7. presentation/schemas.py - request/response shapes
8. app/di.py              - register service
9. app/routers.py         - include router
```

```bash
# After each change, check the module
uv run ruff check app/modules/<name>/
uv run mypy app/modules/<name>/
```

---

## integrate: Add a third-party provider

```bash
# Step 1: Create adapter directory
mkdir -p app/modules/<module>/infrastructure/providers/<vendor>
```

Files to create:
```
config.py       - Pydantic settings
client.py       - raw transport (no domain types)
dtos.py         - vendor response shapes
mapping.py      - DTO -> domain entity
errors.py       - vendor exceptions -> DomainError subclass
adapter.py      - implements the port
```

```bash
# Step 2: Verify no SDK leaks into domain/application
grep -r "import ccxt\|import redis\|import sqlalchemy" \
  app/modules/<module>/domain/ \
  app/modules/<module>/application/
# Should return nothing
```

```bash
# Step 3: Run gates
uv run lint-imports && uv run ruff check app && uv run mypy app
uv run pytest -m integration
```

---

## test: Run validation gates

```bash
# Minimal gate (always run)
uv run ruff check app tests && uv run mypy app && uv run lint-imports && uv run pytest -q

# Integration (when touching adapters/stores/bus)
uv run pytest -m integration

# Full stack
uv run pytest -m e2e

# Single module
uv run ruff check app/modules/<name>/ && uv run mypy app/modules/<name>/ && uv run pytest tests/ -k <name>

# Web
pnpm --dir web lint && pnpm --dir web exec tsc --noEmit && pnpm --dir web exec playwright test

# Security
pip-audit && gitleaks detect
```

Gate selection:
| Change | Gates |
|---|---|
| Domain entity | ruff, mypy, unit |
| New use-case | ruff, mypy, lint-imports, unit |
| New adapter | ruff, mypy, lint-imports, integration |
| New route | ruff, mypy, lint-imports, API test |
| New slice | all backend gates |

---

## db: Schema migrations (flow by flow)

Each feature flow that touches Postgres lands its tables as one numbered Alembic
revision, generated from the ORM models. Autogenerate reads `Base.metadata`
(`app/infrastructure/capability/database/base.py`), and `migrations/env.py`
imports every slice's model module so its tables are seen. The `include_object`
guard keeps autogenerate from touching tables this app does not own.

```bash
# 1. Define/change models: inherit from `Base`, then
uv run alembic revision --autogenerate --rev-id 01 -m "feature flow tables"  # 00, 01, 02... in order
uv run alembic upgrade head   # apply to the configured DATABASE_URL (Neon/CI/local)
uv run alembic current        # show the applied revision
uv run alembic downgrade -1   # roll back exactly one revision
uv run alembic check          # CI drift guard: fails if models and migrations disagree
```

Existing revisions: `00_auth_users_and_api_keys.py` (auth users + api_keys).

---

## check: Quick architecture check

```bash
# Import contracts
uv run lint-imports

# Unused imports
uv run ruff check app --select F401

# SDK leaks in domain/application
grep -rn "import ccxt\|import redis\|import sqlalchemy\|import fastapi" \
  app/modules/*/domain/ app/modules/*/application/

# Cross-module violations
grep -rn "from app.modules\.\(.*\)\.\(infrastructure\|application\|presentation\)" \
  app/modules/ --include="*.py" | grep -v "contracts"
```

---

## refactor: Refactor existing code

Rules before starting:
1. Read the current module structure first
2. Preserve all existing behavior
3. Change one thing at a time
4. Run gates after each change
5. Do not rename unrelated code
6. Do not create new abstractions unless proven necessary

```bash
# After refactoring
uv run ruff check app tests && uv run mypy app && uv run lint-imports && uv run pytest -q
```

---

## scaffold-web: Scaffold the web app (when needed)

```bash
# web/ is not scaffolded yet. When a task needs it:
npx create-next-app@latest web --typescript --tailwind --app --src-dir=false
cd web && pnpm add jose
```

```bash
# Verify Next.js 16 setup
cd web && pnpm exec next --version  # should be 16.x
```

Key rules:
- proxy.ts NOT middleware.ts (Next.js 16)
- Server Components by default
- Never use NEXT_PUBLIC_ for secrets
- Never call backend from client components
- Always auth at proxy AND page/route handler

---

## Secrets check

```bash
# Never log, commit, or record secrets
gitleaks detect
grep -rn "api_key\|secret\|password\|token" app/ --include="*.py" | grep -v "SecretStr\|get_secret_value\|settings\.\|config\.\|__pycache__"
```

## quality: Run quality audit

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

# Coverage
uv run pytest --cov=app --cov-report=term-missing
```
