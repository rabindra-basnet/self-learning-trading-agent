---
name: scaffold
description: Scaffold a new business module. Run new_slice.py, update pyproject.toml contracts, wire composition root.
---

# New Module Scaffold

Load this skill: when creating a brand new business module from scratch.

---

## Before Scaffolding

1. Verify the capability does not belong to an existing module.
2. The module must own a distinct business vocabulary and distinct events.

## Run the Scaffold Script

```bash
# By name
uv run python .agents/scripts/new_slice.py <name> --repo .

# By description
uv run python .agents/scripts/new_slice.py --about "social media sentiment scoring" --repo .

# Preview only
uv run python .agents/scripts/new_slice.py --about "order execution" --repo . --dry-run
```

This creates:

```
modules/<name>/
  presentation/     routes.py, schemas.py
  application/      services.py
  domain/           entities.py, ports.py
  infrastructure/   stores/in_memory.py
  contracts/        __init__.py
```

## After Scaffolding (Manual Steps)

### 1. Update pyproject.toml

Three edits in `[tool.importlinter]`:

a) New slice contract:
```toml
[[tool.importlinter.contracts]]
name = "<name> stays internal to its slice"
type = "forbidden"
source_modules = [
  "app.modules.<name>.domain",
  "app.modules.<name>.application",
  "app.modules.<name>.presentation",
]
forbidden_modules = [
  "app.modules.auth",
  "app.modules.marketdata",
  # ... all other slices
  "app.infrastructure",
]
```

b) Add `"app.modules.<name>"` to every other slice's `forbidden_modules`.

c) Add `"app.modules.<name>.domain"` and `"app.modules.<name>.application"` to the provider-free contract's `source_modules`.

### 2. Wire Composition Root

`app/di.py` - register under the slice's comment block:
```python
# --- <name> --------------------------------------------------------
<name>_store = InMemory<Name>Store()
container.register_instance(InMemory<Name>Store, <name>_store)
container.register(
    <Name>Service,
    lambda: <Name>Service(<name>_store, _bus(container)),
)
```

`app/routers.py` - include the router:
```python
from app.modules.<name>.presentation.routes import router as <name>_router
api_router.include_router(<name>_router)
```

### 3. Verify

```bash
uv run lint-imports && uv run ruff check app && uv run mypy app && uv run pytest -q
```
