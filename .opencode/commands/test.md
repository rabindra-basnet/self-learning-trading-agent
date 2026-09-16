---
description: Run tests and validation gates
---

Load the testing skill first:

skill({ name: "testing" })

Run validation gates for:

$ARGUMENTS

Select the appropriate gates based on what changed:
- Domain only: ruff, mypy, unit
- New use-case: ruff, mypy, lint-imports, unit
- New adapter: ruff, mypy, lint-imports, integration
- New route: ruff, mypy, lint-imports, API test
- New slice: all backend gates

Run them and report results.
