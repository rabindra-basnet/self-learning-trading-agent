---
description: Load architecture rules and review code for violations
---

Load the architecture skill first:

skill({ name: "architecture" })

Then review the following for architectural violations:

$ARGUMENTS

Check for:
- Domain importing infrastructure, FastAPI, SDKs
- Application importing concrete implementations
- Presentation containing business logic
- Cross-module leakage
- Abstraction explosions
- Feature code dumped into core/

Report each violation with: what, why, correct boundary, minimal fix.
