---
description: Quick architecture check on a module
---

Run a quick architecture check:

1. Check imports: uv run ruff check app/modules/$ARGUMENTS --select F401,F811
2. Check types: uv run mypy app/modules/$ARGUMENTS
3. Check lint contracts: uv run lint-imports
4. Check for SDK leaks: grep -r "import ccxt\|import redis\|import sqlalchemy\|import fastapi" app/modules/$ARGUMENTS/domain/ app/modules/$ARGUMENTS/application/

Report any violations.
