---
name: refactoring
description: Refactoring rules. Preserve behavior, refactor incrementally, no speculative abstractions.
---

# Refactoring

Load this skill: when asked to refactor, clean up, or restructure existing code.

---

## Rules

1. Preserve behavior. The refactor must not change what the code does.
2. Understand the current module first. Read its presentation/, application/, domain/, infrastructure/.
3. Refactor incrementally. Small changes, each passing all gates.
4. Do not rename unrelated code.
5. Do not introduce speculative abstractions. Only create abstractions that solve a proven problem.
6. Keep public contracts stable unless the change is intentional.
7. Update tests to match new structure.
8. Remove obsolete code only after the replacement works and passes all gates.

## What NOT to Do

- Do not rewrite the architecture because another architecture looks cleaner.
- Do not move code to `core/` unless it is genuinely shared by multiple modules.
- Do not create BaseXxx, GenericXxx, XxxFactory unless the existing codebase already uses that pattern.
- Do not rename `presentation/` to `api/` or vice versa. The convention is `presentation/`.

## After Refactoring

Run the relevant gates:
```bash
uv run ruff check app tests
uv run mypy app
uv run lint-imports
uv run pytest -q
```

If the refactor touched adapter boundaries:
```bash
uv run pytest -m integration
```
