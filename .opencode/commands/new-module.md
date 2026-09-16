---
description: Scaffold a new business module
---

Load the scaffold skill first:

skill({ name: "scaffold" })

Create a new module for:

$ARGUMENTS

Steps:
1. Run: uv run python .agents/scripts/new_slice.py $ARGUMENTS --repo .
2. Update pyproject.toml import-linter contracts (3 places)
3. Wire app/di.py and app/routers.py
4. Run: uv run lint-imports && uv run ruff check app && uv run mypy app
