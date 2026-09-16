---
description: Check and fix import issues
---

Fix import issues in:

$ARGUMENTS

Steps:
1. Run: uv run ruff check app --select F401,F811 --fix
2. Run: uv run ruff check app/modules/$ARGUMENTS
3. Run: uv run lint-imports
4. Report what was fixed and what remains
